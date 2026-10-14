import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aminos import orchestrator as orch
from aminos.orchestrator import analyse, execute_action, run_cycle, subprocess_runner

NOW = datetime(2026, 10, 13, 14, 59, tzinfo=timezone.utc)


def fake_runner(cpu=12.0, free_mb=8000.0, docker=None, events=None, calls=None):
    """Canned outputs for every collector; `calls` records what was run."""
    docker = docker if docker is not None else []

    def run(tool, command):
        if calls is not None:
            calls.append((tool, command))
        if tool == "powershell":
            if "Get-Counter" in command:
                return 0, json.dumps([{"Path": "\\\\h\\memory\\available mbytes", "CookedValue": free_mb},
                                      {"Path": "\\\\h\\processor(_total)\\% processor time", "CookedValue": cpu}])
            if "Get-WinEvent" in command:
                return 0, json.dumps(events or [])
            if "Win32_OperatingSystem" in command:
                return 0, json.dumps({"TotalVisibleMemorySize": 16000000, "FreePhysicalMemory": int(free_mb * 1024)})
            return 0, json.dumps([])
        if tool == "docker" and command.startswith("ps"):
            return 0, "\n".join(json.dumps({"Names": d["name"], "Status": d["status"], "Ports": ""}) for d in docker)
        if tool == "docker" and command.startswith("inspect"):
            d = next(x for x in docker if x["name"] == command.split()[-1])
            return 0, f"{d['restarts']}|{d['exit']}"
        if tool == "nvidia-smi":
            return 127, "nvidia-smi: not installed"
        if tool == "kubectl":
            return 127, "kubectl: not installed"
        if tool == "git":
            return 0, "## main...origin/main"
        if tool == "python":
            return 0, "3.12.10"
        return 0, ""
    return run


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.log = Path(tempfile.mkdtemp())

    def test_quiet_machine_means_no_action(self):
        rec = run_cycle(fake_runner(), self.log, now=NOW)
        self.assertEqual((rec["decision"], rec["actions"], rec["alerts"], rec["next_check_seconds"]), ("Aucune action", [], [], 300))
        self.assertEqual(rec["cycle_id"], "orch-001")
        self.assertEqual(rec["timestamp"], "2026-10-13T14:59:00Z")

    def test_record_has_the_specified_shape_and_is_logged_as_jsonl(self):
        rec = run_cycle(fake_runner(), self.log, now=NOW)
        run_cycle(fake_runner(), self.log, now=NOW)
        for k in ("timestamp", "cycle_id", "observations", "analysis", "decision", "actions", "next_check_seconds"):
            self.assertIn(k, rec)
        for k in ("cpu_top", "mem", "gpu", "docker", "k8s", "logs_critical", "net_listen", "git_status", "py_check"):
            self.assertIn(k, rec["observations"])
        lines = (self.log / "orch-2026-10-13.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(l)["cycle_id"] for l in lines], ["orch-001", "orch-002"])

    def test_thresholds(self):
        self.assertIn("CPU 95%", analyse({"counters": [{"Path": "x processor time", "CookedValue": 95}]})[1][0])
        self.assertEqual(analyse({"counters": [{"Path": "x processor time", "CookedValue": 90}]})[1], [])   # strictly above
        self.assertIn("499", analyse({"counters": [{"Path": "available mbytes", "CookedValue": 499}]})[1][0])
        self.assertEqual(analyse({"counters": [{"Path": "available mbytes", "CookedValue": 500}]})[1], [])
        containers = lambda n: {"docker": [{"name": "c", "status": "Up 1h", "restart_count": n, "exit_code": 0}]}
        self.assertEqual(analyse(containers(3))[1], [])
        self.assertEqual(len(analyse(containers(4))[1]), 1)

    def test_memory_falls_back_to_cim_when_counters_fail(self):
        obs = {"counters": {"error": "x"}, "mem": [{"FreePhysicalMemory": 100 * 1024}]}
        self.assertIn("100", analyse(obs)[1][0])

    def test_log_alert_only_for_errors_inside_five_minutes(self):
        ev = lambda minutes, level: {"TimeCreated": f"2026-10-13T{14 if minutes < 59 else 13}:{59 - minutes:02d}:00Z"
                                     if minutes < 59 else "2026-10-13T13:00:00Z", "Id": 7, "Level": level, "Message": "m"}
        self.assertEqual(len(analyse({"logs_critical": [ev(2, 2)]}, NOW)[1]), 1)
        self.assertEqual(analyse({"logs_critical": [ev(2, 3)]}, NOW)[1], [])   # warning: collected, not alerting
        self.assertEqual(analyse({"logs_critical": [ev(30, 1)]}, NOW)[1], [])  # too old

    def test_exit_137_proposes_restart_but_dry_run_does_not_run_it(self):
        calls = []
        docker = [{"name": "web", "status": "Exited (137) 2 minutes ago", "restarts": 0, "exit": 137}]
        rec = run_cycle(fake_runner(docker=docker, calls=calls), self.log, now=NOW)
        self.assertEqual(rec["decision"], "Redémarrer service web")
        a = rec["actions"][0]
        self.assertEqual((a["command"], a["executed"]), ("docker restart web", False))
        self.assertIn("dry-run", a["status"])
        self.assertNotIn(("docker", "restart web"), calls)

    def test_execute_runs_only_allow_listed_commands(self):
        calls = []
        run = fake_runner(calls=calls)
        ok = execute_action(run, {"tool": "docker", "command": "docker restart web"}, execute=True)
        self.assertTrue(ok["executed"])
        for bad in ("Remove-Item C:\\ -Recurse", "Restart-Service -Name 'sshd'", "docker restart web; rm -rf /",
                    "docker rm web", "Restart-Service -Name 'wuauserv'; Stop-Computer"):
            r = execute_action(run, {"tool": "powershell", "command": bad}, execute=True)
            self.assertFalse(r["executed"], bad)
            self.assertIn("refused", r["status"])
        self.assertEqual([c for c in calls if c[0] == "powershell" and "Remove-Item" in c[1]], [])

    def test_failing_collectors_never_stop_the_cycle_and_never_report_all_clear(self):
        def broken(tool, command):
            return 1, "boom"
        rec = run_cycle(broken, self.log, now=NOW)
        self.assertIn("error", rec["observations"]["cpu_top"])
        self.assertEqual(rec["decision"], "Alerter utilisateur")  # "nothing measured" is not "nothing wrong"
        self.assertIn("indisponibles", rec["alerts"][0])

    def test_alert_speeds_up_next_check(self):
        rec = run_cycle(fake_runner(cpu=97), self.log, interval=300, now=NOW)
        self.assertEqual((rec["decision"], rec["next_check_seconds"]), ("Lancer diagnostic approfondi", 60))

    def test_loop_runs_requested_cycles(self):
        out, slept = [], []
        n = orch.loop(fake_runner(), self.log, 5, False, max_cycles=3, sleep=slept.append, emit=out.append)
        self.assertEqual((n, slept, len(out)), (3, [5, 5], 3))

    def test_real_runner_refuses_unknown_tools_and_survives_missing_ones(self):
        run = subprocess_runner()
        self.assertEqual(run("rm", "-rf /")[0], 126)
        self.assertIn(run("nvidia-smi", "--version")[0], (0, 1, 127))


if __name__ == "__main__":
    unittest.main()
