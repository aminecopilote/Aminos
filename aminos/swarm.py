"""Multi-agent job runner: specialised agents on SuperInstance/agent-coordinator, re-run until the result is sound.

Roles: extractor, terminologist, translator (N in parallel), reviewer, notary.
agent-coordinator has no retry of its own (a failed task simply comes back with success=False), so the
"repeat until conclusive" loop lives here: every round re-submits only the chunks whose review still
reports issues, escalating through a ladder of (mode, model) strategies. When the ladder is exhausted
the job is reported as NOT ok with the issues that remain; it is never presented as a success.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import pipeline
from .glossary import Glossary
from .llm import Chat
from .tm import TranslationMemory

try:  # optional extra: pip install -e ".[swarm]"
    from agent_coordinator.agent import AgentRole
    from agent_coordinator.coordinator import AgentCoordinator, CoordinatorConfig
    from agent_coordinator.task import Task
    HAVE_COORDINATOR = True
except ImportError:
    HAVE_COORDINATOR = False

ROLES = {"extractor": "extract", "terminologist": "terms", "translator": "translate",
         "reviewer": "review", "notary": "notarize"}


@dataclass
class Strategy:
    mode: str
    chat: int  # index into the list of chats, clipped to the last one


DEFAULT_LADDER = (Strategy("normal", 0), Strategy("hard", 0), Strategy("hard", 1))


class Swarm:
    """Async context manager owning one coordinator and its agents."""

    def __init__(self, translators: int = 3, task_timeout: float = 600.0):
        if not HAVE_COORDINATOR:
            raise RuntimeError('agent-coordinator is not installed: pip install -e ".[swarm]"')
        self.translators, self.task_timeout = translators, task_timeout
        self.coord = AgentCoordinator(CoordinatorConfig(name="aminos", task_processing_interval=0.01))

    async def __aenter__(self) -> "Swarm":
        await self.coord.start()
        for role, cap in ROLES.items():
            if role == "translator":
                # One role per translator with its own capability: agent-coordinator marks an agent busy only
                # when its worker starts the task, so one dispatch pass piles every task on the first idle
                # agent. Explicit round-robin sharding (see run_many) is what gives real parallelism.
                for i in range(self.translators):
                    await self.coord.register_role(AgentRole(name=f"{role}-{i + 1}", capabilities=[cap, f"{cap}-{i}"]))
                    await self.coord.spawn_agent(f"{role}-{i + 1}", role=f"{role}-{i + 1}", task_handler=self._handler,
                                                 task_timeout=self.task_timeout)
            else:
                await self.coord.register_role(AgentRole(name=role, capabilities=[cap]))
                await self.coord.spawn_agent(f"{role}-1", role=role, task_handler=self._handler,
                                             task_timeout=self.task_timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        await self.coord.shutdown()

    @staticmethod
    async def _handler(task: "Task") -> Any:
        return await asyncio.to_thread(task.payload["fn"])  # blocking work must not stall the event loop

    async def run_many(self, capability: str, fns: list[Callable[[], Any]], label: str = "",
                       spread: bool = False) -> list[tuple[bool, Any]]:
        """Run callables on agents holding `capability`; returns (success, result-or-error) in order.

        spread=True deals the callables round-robin to the translator agents so they run concurrently.
        """
        tasks = [Task(description=f"{label}#{i}",
                      required_capabilities=[f"{capability}-{i % self.translators}" if spread else capability],
                      payload={"fn": fn}, timeout=self.task_timeout) for i, fn in enumerate(fns)]
        results = await self.coord.submit_tasks(tasks, wait_for_all=True)
        return [(r.success, r.result if r.success else r.error) for r in results]

    async def run_one(self, capability: str, fn: Callable[[], Any], label: str = "") -> Any:
        ok, value = (await self.run_many(capability, [fn], label))[0]
        if not ok:
            raise RuntimeError(f"{capability} task failed: {value}")
        return value


@dataclass
class JobReport:
    ok: bool
    paragraphs: list[str]
    rounds: list[dict] = field(default_factory=list)
    remaining_issues: list[str] = field(default_factory=list)
    reused_from_tm: int = 0
    docx: str = ""
    notary: dict | None = None


async def run_job(paragraphs: list[str], source_lang: str, target_lang: str, chats: list[Chat],
                  glossary: Glossary | None = None, tm: TranslationMemory | None = None,
                  ladder: tuple[Strategy, ...] = DEFAULT_LADDER, jurisdiction: str = "", translators: int = 3,
                  max_chars: int = 1800, reuse_threshold: float = 0.98,
                  docx_out: str | Path | None = None, notarize: Callable[[Path], dict] | None = None) -> JobReport:
    """Translate `paragraphs`, review, and re-run failing chunks along `ladder` until clean or exhausted."""
    gloss = glossary or Glossary()
    out: list[str] = [""] * len(paragraphs)
    report = JobReport(ok=False, paragraphs=out)

    async with Swarm(translators) as sw:
        # terminologist: which imposed terms apply (also warms the matcher); TM reuse happens here too
        todo: list[int] = []
        for i, para in enumerate(paragraphs):
            hit = tm.lookup(para, source_lang, target_lang, reuse_threshold, 1) if tm is not None else []
            if hit:
                out[i] = hit[0].target
                report.reused_from_tm += 1
            else:
                todo.append(i)
        await sw.run_one("terms", lambda: len(gloss.find("\n".join(paragraphs[i] for i in todo))), "terms")

        chunks = [[todo[j] for j in idx] for idx in _index_chunks([paragraphs[i] for i in todo], max_chars)]
        pending = list(range(len(chunks)))
        issues_by_chunk: dict[int, list[str]] = {}

        for rnd, strat in enumerate(ladder, 1):
            if not pending:
                break
            chat = chats[min(strat.chat, len(chats) - 1)]

            def job(c: int, mode: str = strat.mode, chat: Chat = chat):
                srcs = [paragraphs[i] for i in chunks[c]]
                return lambda: pipeline.translate_chunk(chat, srcs, source_lang, target_lang, gloss, mode,
                                                        jurisdiction).translations

            results = await sw.run_many("translate", [job(c) for c in pending], f"r{rnd}", spread=True)
            reviews = []
            for c, (ok, value) in zip(pending, results):
                if ok:
                    for i, t in zip(chunks[c], value):
                        out[i] = t
                reviews.append((c, ok, value))
            # reviewer: independent deterministic check of what the translators returned
            verdicts = await sw.run_many("review", [
                (lambda c=c: pipeline.deterministic_issues(gloss, [paragraphs[i] for i in chunks[c]],
                                                            [out[i] for i in chunks[c]])) for c, _, _ in reviews], "review")
            still = []
            for (c, ok, value), (rok, verdict) in zip(reviews, verdicts):
                problems = (verdict if rok else [f"revue impossible : {verdict}"]) if ok else [f"traduction impossible : {value}"]
                if problems:
                    issues_by_chunk[c] = problems
                    still.append(c)
                else:
                    issues_by_chunk.pop(c, None)
                    if tm is not None:
                        for i in chunks[c]:
                            tm.add(paragraphs[i], out[i], source_lang, target_lang, origin="swarm")
            report.rounds.append({"round": rnd, "mode": strat.mode, "chat": min(strat.chat, len(chats) - 1),
                                  "chunks_run": len(pending), "chunks_clean": len(pending) - len(still)})
            pending = still

        report.remaining_issues = [f"bloc {c + 1} : {m}" for c in sorted(issues_by_chunk) for m in issues_by_chunk[c]]
        report.ok = not pending

        if docx_out is not None:
            from .docx_out import build_docx
            await sw.run_one("notarize", lambda: build_docx(out, target_lang, str(docx_out)), "docx")
            report.docx = str(docx_out)
            if notarize is not None and report.ok:  # only a clean translation is sealed
                report.notary = await sw.run_one("notarize", lambda: notarize(Path(docx_out)), "notarize")
    return report


def _index_chunks(paragraphs: list[str], max_chars: int) -> list[list[int]]:
    """Chunk like the pipeline does, but return paragraph positions instead of text."""
    chunks, pos = [], 0
    for chunk in pipeline.chunk_paragraphs(paragraphs, max_chars):
        chunks.append(list(range(pos, pos + len(chunk))))
        pos += len(chunk)
    return chunks
