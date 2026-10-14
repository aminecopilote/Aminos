import ast
import json
import re
import unittest
from pathlib import Path

from aminos import colab

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "aminos_colab_gpu.ipynb"


def smi(out, rc=0):
    return lambda argv: (rc, out)


class ColabTests(unittest.TestCase):
    def test_t4_gets_the_largest_model(self):
        p = colab.plan(smi("Tesla T4, 15360, 15101\n"))
        self.assertEqual((p.gpu, p.vram_total_mb, p.model), ("Tesla T4", 15360, "qwen3:14b"))

    def test_p100_16gb(self):
        self.assertEqual(colab.plan(smi("Tesla P100-PCIE-16GB, 16384, 16000\n")).model, "qwen3:14b")

    def test_model_is_chosen_from_FREE_memory_not_total(self):
        self.assertEqual(colab.plan(smi("Tesla T4, 15360, 9000\n")).model, "qwen3:8b")  # another process holds 6 GB

    def test_small_cards(self):
        for free, model in ((6000, "qwen3:4b"), (3000, "qwen3:1.7b"), (7999, "qwen3:4b"), (8000, "qwen3:8b"), (14000, "qwen3:14b")):
            self.assertEqual(colab.choose_model(free)[0], model, free)

    def test_no_gpu_says_so_and_warns(self):
        p = colab.plan(smi("", rc=127))
        self.assertEqual(p.gpu, "none")
        self.assertIn("Change runtime type", p.warnings[0])

    def test_confidentiality_warning_is_always_present(self):
        for run in (smi("Tesla T4, 15360, 15000\n"), smi("", 127)):
            self.assertTrue(any("leaves your machine" in w for w in colab.plan(run).warnings))


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_valid_nbformat_with_colab_gpu_metadata(self):
        self.assertEqual(self.nb["nbformat"], 4)
        self.assertEqual(self.nb["metadata"]["accelerator"], "GPU")
        self.assertTrue(all("outputs" in c and "execution_count" in c for c in self.nb["cells"] if c["cell_type"] == "code"))

    def test_every_code_cell_compiles(self):
        for i, c in enumerate(c for c in self.nb["cells"] if c["cell_type"] == "code"):
            src = "".join(c["source"])
            lines = [("pass" if l.lstrip().startswith(("!", "%")) else l) for l in src.splitlines()]  # shell/magic lines
            try:
                ast.parse("\n".join(lines))
            except SyntaxError as e:
                self.fail(f"code cell {i}: {e}")

    def test_warns_about_confidentiality_and_exposes_nothing(self):
        text = "\n".join("".join(c["source"]) for c in self.nb["cells"]).lower()
        self.assertIn("confidenti", text)
        for forbidden in ("ngrok", "cloudflared", "localtunnel", "--share"):
            self.assertNotIn(forbidden, text)  # Colab forbids using free runtimes as a public server or proxy

    def test_no_secret_is_hard_coded(self):
        text = "\n".join("".join(c["source"]) for c in self.nb["cells"])
        self.assertIsNone(re.search(r"(sk-[A-Za-z0-9]{10,}|api[_-]?key\s*=\s*['\"][A-Za-z0-9]{10,})", text))


GPU_TEST = ROOT / "notebooks" / "OpenClaw-GPU-Test.ipynb"


class FakeTensor:
    def __matmul__(self, other):
        return FakeTensor()


def fake_torch(has_gpu):
    import types
    t = types.ModuleType("torch")
    t.cuda = types.SimpleNamespace(
        is_available=lambda: has_gpu, get_device_name=lambda i: "Tesla T4",
        get_device_properties=lambda i: types.SimpleNamespace(total_memory=15 * 1024 ** 3 + 100 * 1024 ** 2),
        synchronize=lambda: None, empty_cache=lambda: None)
    t.randn = lambda shape, device=None: FakeTensor()
    return t


class GpuTestNotebookTests(unittest.TestCase):
    """The notebook's cells are run against a stand-in torch: logic of both branches, not a real GPU."""

    def cells(self):
        nb = json.loads(GPU_TEST.read_text(encoding="utf-8"))
        return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]

    def run_cell(self, src, has_gpu):
        import contextlib, io, sys
        buf = io.StringIO()
        old = sys.modules.get("torch")
        sys.modules["torch"] = fake_torch(has_gpu)
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(src, "cell", "exec"), {})
        finally:
            sys.modules.pop("torch", None)
            if old is not None:
                sys.modules["torch"] = old
        return buf.getvalue()

    def test_three_code_cells_in_order(self):
        c = self.cells()
        self.assertEqual(len(c), 3)
        self.assertTrue(c[0].startswith("!nvidia-smi"))

    def test_gpu_present(self):
        c = self.cells()
        out = self.run_cell(c[1], True)
        self.assertIn("GPU disponible : True", out)
        self.assertIn("Modèle : Tesla T4", out)
        self.assertIn("VRAM : 15.1 Gio", out)
        self.assertRegex(self.run_cell(c[2], True), r"Calcul GPU réussi en \d+\.\d{3} seconde\(s\)")

    def test_no_gpu(self):
        c = self.cells()
        self.assertIn("Vérifiez que le type d’exécution utilise un GPU.", self.run_cell(c[1], False))
        self.assertIn("Aucun GPU disponible pour ce test.", self.run_cell(c[2], False))

    def test_sends_nothing_and_asks_nothing(self):
        text = "\n".join("\n".join(self.cells()))
        for forbidden in ("files.upload", "drive.mount", "requests", "urllib", "subprocess", "pip install"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
