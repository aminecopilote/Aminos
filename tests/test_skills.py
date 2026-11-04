import subprocess
import tempfile
import unittest
from pathlib import Path

from aminos.skills import SkillError, SkillManager, discover, parse_frontmatter, search_index

SKILL = "---\nname: {n}\ndescription: {d}\n---\n# {n}\nUse it.\n"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(tmp: Path) -> Path:
    r = tmp / "repo"
    (r / "alpha" / "references").mkdir(parents=True)
    (r / "alpha" / "scripts").mkdir()
    (r / "beta").mkdir()
    (r / "alpha" / "SKILL.md").write_text(SKILL.format(n="alpha", d="first"))
    (r / "alpha" / "references" / "guide.md").write_text("guide v1")
    (r / "alpha" / "scripts" / "run.py").write_text("print('x')")
    (r / "alpha" / "tool.exe").write_bytes(b"MZ")
    (r / "beta" / "SKILL.md").write_text(SKILL.format(n="beta", d="second"))
    git(r.parent, "init", "-q", str(r))
    git(r, "add", "-A"); git(r, "commit", "-q", "-m", "v1")
    return r


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = make_repo(self.tmp)
        self.mgr = SkillManager(self.tmp / "skills")
        self.spec = str(self.repo)

    def test_frontmatter_and_discovery(self):
        self.assertEqual(parse_frontmatter(SKILL.format(n="a", d="b"))["description"], "b")
        self.assertEqual(sorted(s.name for s in discover(self.repo)), ["alpha", "beta"])

    def test_install_copies_text_only_and_reports_skipped(self):
        report = self.mgr.install(self.spec, ["alpha"])
        key, skipped = report[0]
        base = self.mgr.dest / key
        self.assertTrue((base / "SKILL.md").exists() and (base / "references" / "guide.md").exists())
        self.assertFalse((base / "scripts" / "run.py").exists())
        self.assertFalse((base / "tool.exe").exists())
        self.assertTrue(any("run.py" in s and "--with-scripts" in s for s in skipped), skipped)
        meta = self.mgr.installed()[key]
        self.assertRegex(meta["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(set(meta["files"]), {"SKILL.md", "references/guide.md"})

    def test_scripts_only_when_explicit_and_executables_never(self):
        key = self.mgr.install(self.spec, ["alpha"], with_scripts=True)[0][0]
        self.assertTrue((self.mgr.dest / key / "scripts" / "run.py").exists())

    def test_must_name_skill_when_several(self):
        with self.assertRaisesRegex(SkillError, "name the ones to install"):
            self.mgr.install(self.spec)
        with self.assertRaisesRegex(SkillError, "not in"):
            self.mgr.install(self.spec, ["nope"])

    def test_install_pins_requested_commit(self):
        first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout.strip()
        (self.repo / "alpha" / "references" / "guide.md").write_text("guide v2")
        git(self.repo, "commit", "-qam", "v2")
        self.mgr.install(self.spec, ["alpha"], ref=first)
        key = next(iter(self.mgr.installed()))
        self.assertEqual((self.mgr.dest / key / "references" / "guide.md").read_text(), "guide v1")
        self.assertEqual(self.mgr.installed()[key]["commit"], first)

    def test_verify_detects_local_edit_and_deletion(self):
        key = self.mgr.install(self.spec, ["alpha"])[0][0]
        self.assertEqual(self.mgr.verify(), [])
        (self.mgr.dest / key / "SKILL.md").write_text("tampered")
        (self.mgr.dest / key / "references" / "guide.md").unlink()
        self.assertEqual(len(self.mgr.verify()), 2)

    def test_update_shows_plan_first_then_applies(self):
        key = self.mgr.install(self.spec, ["alpha"])[0][0]
        (self.repo / "alpha" / "references" / "guide.md").write_text("guide v2")
        (self.repo / "alpha" / "references" / "new.md").write_text("new")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-qm", "v2")
        plan = self.mgr.update(key)  # dry run
        self.assertEqual((plan.changed, plan.added, plan.removed), (["references/guide.md"], ["references/new.md"], []))
        self.assertEqual((self.mgr.dest / key / "references" / "guide.md").read_text(), "guide v1")  # untouched
        self.mgr.update(key, apply=True)
        self.assertEqual((self.mgr.dest / key / "references" / "guide.md").read_text(), "guide v2")
        self.assertEqual(self.mgr.verify(), [])
        self.assertTrue(self.mgr.update(key).empty)

    def test_update_refuses_to_overwrite_local_edits(self):
        key = self.mgr.install(self.spec, ["alpha"])[0][0]
        (self.mgr.dest / key / "references" / "guide.md").write_text("my notes")
        (self.repo / "alpha" / "references" / "guide.md").write_text("guide v2")
        git(self.repo, "commit", "-qam", "v2")
        with self.assertRaisesRegex(SkillError, "locally modified"):
            self.mgr.update(key, apply=True)
        self.assertEqual((self.mgr.dest / key / "references" / "guide.md").read_text(), "my notes")
        self.mgr.update(key, apply=True, force=True)
        self.assertEqual((self.mgr.dest / key / "references" / "guide.md").read_text(), "guide v2")

    def test_symlink_is_not_followed(self):
        link = self.repo / "alpha" / "references" / "secret.md"
        link.symlink_to("/etc/passwd")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-qm", "link")
        key, skipped = self.mgr.install(self.spec, ["alpha"])[0]
        self.assertFalse((self.mgr.dest / key / "references" / "secret.md").exists())
        self.assertTrue(any("symlink" in s for s in skipped))

    def test_remove(self):
        key = self.mgr.install(self.spec, ["beta"])[0][0]
        self.mgr.remove(key)
        self.assertFalse((self.mgr.dest / key).exists() or self.mgr.installed())

    def test_resolve_and_index_search(self):
        self.assertEqual(SkillManager.resolve("owner/repo")[1], "https://github.com/owner/repo.git")
        label, url, ref, sub = SkillManager.resolve("https://github.com/o/r/tree/main/skills/x")
        self.assertEqual((url, ref, sub), ("https://github.com/o/r.git", "main", "skills/x"))
        with self.assertRaises(SkillError):
            SkillManager.resolve("not a source")
        readme = ("- **[a/pdf](https://officialskills.sh/a/skills/pdf)** - Handle PDF files\n"
                  "- **[b/pdf-fill](https://github.com/b/r/tree/main/pdf-fill)** - Fill PDF forms\n"
                  "- **[c/other](https://github.com/c/r/tree/main/o)** - Something else\n")
        hits = search_index(readme, "pdf")
        self.assertEqual([(h["name"], h["installable"]) for h in hits], [("a/pdf", False), ("b/pdf-fill", True)])


if __name__ == "__main__":
    unittest.main()
