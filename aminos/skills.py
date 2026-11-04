"""Install, verify and update third-party agent skills (SKILL.md folders) from Git repositories.

Third-party skills are untrusted input: they can carry prompt injections or malicious scripts. This manager therefore
  * pins every install to a commit and records it, with a SHA-256 per file, in skills.lock.json;
  * copies text files only (.md .txt .json .yaml .yml .csv) unless --with-scripts is given explicitly;
  * refuses symlinks, absolute paths and path traversal;
  * never executes anything it downloads;
  * on update, shows what changed and applies it only on request, and never overwrites a file edited locally.
Indexes such as VoltAgent/awesome-agent-skills are lists of links, not skills: `search_index` finds entries and
`install` then fetches the chosen skill from its own repository.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
SCRIPT_SUFFIXES = {".py", ".ps1", ".sh", ".bat", ".cmd", ".js", ".ts", ".exe", ".dll"}
MAX_FILE_BYTES = 2_000_000
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_TREE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/tree/([^/]+)/(.+)$")
_ENTRY = re.compile(r"^- \*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*-\s*(.*)$")

# Known sources. `ref` pins the commit used when the user installs without choosing one; `update` moves it.
SOURCES = {
    "chatgpt-skills": {"url": "https://github.com/dkyazzentwatwa/chatgpt-skills.git",
                       "ref": "103b4308f65df393e76765cb1ce12395d9cf5106",
                       "note": "no LICENSE file in the repository: install on your own machine, do not redistribute"},
    "awesome-agent-skills": {"url": "https://github.com/VoltAgent/awesome-agent-skills.git",
                             "ref": "bca04bcb9d33f8d59cd32300da63787e5594be4a", "index": True,
                             "note": "an index of links (MIT), not a set of skills"},
}


class SkillError(Exception):
    pass


@dataclass
class Skill:
    name: str
    path: Path
    description: str = ""


@dataclass
class UpdatePlan:
    skill: str
    old_commit: str
    new_commit: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    locally_modified: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: Path | None = None) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as e:
        raise SkillError("git is not installed (Windows: winget install Git.Git)") from e
    if p.returncode:
        raise SkillError(f"git {' '.join(args[:2])} failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def fetch(url: str, dest: Path, ref: str | None = None) -> str:
    """Shallow-fetch `url` into dest at `ref` (commit, branch or None for default); return the commit SHA."""
    if ref and _SHA.match(ref):
        _git("init", "-q", str(dest))
        _git("remote", "add", "origin", url, cwd=dest)
        _git("fetch", "-q", "--depth", "1", "origin", ref, cwd=dest)
        _git("checkout", "-q", "FETCH_HEAD", cwd=dest)
    else:
        _git("clone", "-q", "--depth", "1", *(["--branch", ref] if ref else []), url, str(dest))
    return _git("rev-parse", "HEAD", cwd=dest)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    out: dict[str, str] = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("\"'")
    return out


def discover(repo: Path, subdir: str = "") -> list[Skill]:
    """Folders holding a SKILL.md, up to three levels below `subdir`."""
    root = repo / subdir
    skills = []
    for md in sorted(root.glob("SKILL.md")) + sorted(root.glob("*/SKILL.md")) + sorted(root.glob("*/*/SKILL.md")):
        fm = parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
        name = fm.get("name") or md.parent.name
        if _NAME.match(name):
            skills.append(Skill(name, md.parent, fm.get("description", "")))
    return skills


def _copy_skill(src: Path, dst: Path, with_scripts: bool) -> tuple[dict[str, str], list[str]]:
    """Copy allowed files; return ({relative path: sha256}, [skipped paths])."""
    if dst.exists():
        shutil.rmtree(dst)
    files, skipped = {}, []
    for f in sorted(src.rglob("*")):
        rel = f.relative_to(src)
        if f.is_symlink():
            skipped.append(f"{rel} (symlink)")
        elif f.is_dir() or ".git" in rel.parts or "__pycache__" in rel.parts:
            continue
        elif f.stat().st_size > MAX_FILE_BYTES:
            skipped.append(f"{rel} (too large)")
        elif f.suffix.lower() in TEXT_SUFFIXES or (with_scripts and f.suffix.lower() in SCRIPT_SUFFIXES):
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            files[rel.as_posix()] = _sha256(target)
        else:
            skipped.append(f"{rel} ({'script, use --with-scripts after review' if f.suffix.lower() in SCRIPT_SUFFIXES else 'file type not allowed'})")
    if "SKILL.md" not in files:
        raise SkillError(f"{src.name}: no SKILL.md copied")
    return files, skipped


class SkillManager:
    def __init__(self, dest: str | Path):
        self.dest = Path(dest)
        self.lock_path = self.dest / "skills.lock.json"

    # ---- lock file --------------------------------------------------
    def lock(self) -> dict:
        if self.lock_path.exists():
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        return {"skills": {}}

    def _save(self, lock: dict) -> None:
        self.dest.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def installed(self) -> dict[str, dict]:
        return self.lock()["skills"]

    # ---- resolve ----------------------------------------------------
    @staticmethod
    def resolve(spec: str) -> tuple[str, str, str, str]:
        """spec -> (source label, git url, ref or '', subdir). Accepts a known source, owner/repo or a GitHub tree URL."""
        if spec in SOURCES:
            s = SOURCES[spec]
            return spec, s["url"], s.get("ref", ""), ""
        m = _TREE.match(spec)
        if m:
            owner, repo, ref, sub = m.groups()
            return f"{owner}-{repo}", f"https://github.com/{owner}/{repo}.git", ref, sub
        if re.match(r"^[\w.-]+/[\w.-]+$", spec):
            owner, repo = spec.split("/")
            return f"{owner}-{repo}", f"https://github.com/{owner}/{repo}.git", "", ""
        if spec.startswith(("file://", "/")) or re.match(r"^[A-Za-z]:\\", spec):  # local repository (tests, mirrors)
            return Path(spec.replace("file://", "")).name or "local", spec, "", ""
        raise SkillError(f"unknown source: {spec}")

    # ---- operations -------------------------------------------------
    def available(self, spec: str) -> list[Skill]:
        _, url, ref, sub = self.resolve(spec)
        tmp = Path(tempfile.mkdtemp())
        try:
            fetch(url, tmp / "r", ref or None)
            return [Skill(s.name, s.path.relative_to(tmp / "r"), s.description) for s in discover(tmp / "r", sub)]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def install(self, spec: str, names: list[str] | None = None, with_scripts: bool = False,
                ref: str | None = None) -> list[tuple[str, list[str]]]:
        label, url, default_ref, sub = self.resolve(spec)
        tmp = Path(tempfile.mkdtemp())
        try:
            commit = fetch(url, tmp / "r", ref or default_ref or None)
            found = {s.name: s for s in discover(tmp / "r", sub)}
            if not found:
                raise SkillError(f"{spec}: no SKILL.md found")
            wanted = names or ([next(iter(found))] if len(found) == 1 else [])
            if not wanted:
                raise SkillError(f"{spec}: {len(found)} skills available, name the ones to install: {', '.join(sorted(found))}")
            lock, report = self.lock(), []
            for n in wanted:
                if n not in found:
                    raise SkillError(f"{n}: not in {spec} (available: {', '.join(sorted(found))})")
                files, skipped = _copy_skill(found[n].path, self.dest / label / n, with_scripts)
                lock["skills"][f"{label}/{n}"] = {"spec": spec, "url": url, "commit": commit, "subdir": sub,
                                                   "path": found[n].path.relative_to(tmp / "r").as_posix(),
                                                   "with_scripts": with_scripts, "files": files}
                report.append((f"{label}/{n}", skipped))
            self._save(lock)
            return report
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def verify(self) -> list[str]:
        """Files that were modified or deleted since installation."""
        problems = []
        for key, meta in self.installed().items():
            for rel, digest in meta["files"].items():
                p = self.dest / key / rel
                if not p.exists():
                    problems.append(f"{key}/{rel}: missing")
                elif _sha256(p) != digest:
                    problems.append(f"{key}/{rel}: modified locally")
        return problems

    def update(self, key: str, apply: bool = False, force: bool = False) -> UpdatePlan:
        """Compare an installed skill with the newest upstream version; apply only when asked."""
        meta = self.installed().get(key)
        if not meta:
            raise SkillError(f"{key}: not installed")
        tmp = Path(tempfile.mkdtemp())
        try:
            _, url, _, _ = self.resolve(meta["spec"])
            commit = fetch(url, tmp / "r", None)
            src = tmp / "r" / meta["path"]
            if not (src / "SKILL.md").exists():
                raise SkillError(f"{key}: the skill no longer exists upstream")
            new, _ = _copy_skill(src, tmp / "new", meta["with_scripts"])
            old = meta["files"]
            plan = UpdatePlan(key, meta["commit"], commit,
                              added=sorted(set(new) - set(old)), removed=sorted(set(old) - set(new)),
                              changed=sorted(r for r in new if r in old and new[r] != old[r]))
            plan.locally_modified = sorted(r for r in old if (self.dest / key / r).exists()
                                           and _sha256(self.dest / key / r) != old[r])
            if apply and not plan.empty:
                if plan.locally_modified and not force:
                    raise SkillError(f"{key}: locally modified files would be overwritten ({', '.join(plan.locally_modified)}); use --force")
                shutil.rmtree(self.dest / key)
                shutil.copytree(tmp / "new", self.dest / key)
                lock = self.lock()
                lock["skills"][key].update(commit=commit, files=new)
                self._save(lock)
            return plan
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def remove(self, key: str) -> None:
        lock = self.lock()
        if key not in lock["skills"]:
            raise SkillError(f"{key}: not installed")
        shutil.rmtree(self.dest / key, ignore_errors=True)
        del lock["skills"][key]
        self._save(lock)


def search_index(readme: str, keyword: str, limit: int = 30) -> list[dict]:
    """Entries of an awesome-agent-skills style README matching `keyword`; `installable` when the link is a GitHub tree URL."""
    kw, out = keyword.lower(), []
    for line in readme.splitlines():
        m = _ENTRY.match(line.strip())
        if m and kw in line.lower():
            name, url, desc = m.groups()
            out.append({"name": name, "url": url, "description": desc, "installable": bool(_TREE.match(url))})
            if len(out) >= limit:
                break
    return out
