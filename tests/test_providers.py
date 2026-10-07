import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from aminos import providers
from aminos.providers import ProviderError, build_chat, fallback_chat, openai_compatible_chat


def fake_response(text):
    return io.BytesIO(json.dumps({"choices": [{"message": {"content": f" {text} "}}]}).encode())


class ProviderTests(unittest.TestCase):
    def test_remote_refused_without_consent(self):
        with self.assertRaises(PermissionError):
            openai_compatible_chat("ovh")

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                openai_compatible_chat("groq", allow_remote=True)

    def test_request_shape_and_parse(self):
        seen = {}

        def urlopen(req, timeout=0):
            seen["url"], seen["auth"] = req.full_url, req.get_header("Authorization")
            seen["body"] = json.loads(req.data)
            return fake_response("bonjour")
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "k"}), mock.patch("urllib.request.urlopen", urlopen):
            chat = openai_compatible_chat("groq", allow_remote=True)
            self.assertEqual(chat([{"role": "user", "content": "hi"}], "sys"), "bonjour")
        self.assertEqual(seen["url"], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer k")
        self.assertEqual(seen["body"]["messages"][0], {"role": "system", "content": "sys"})

    def test_local_needs_no_consent_nor_key(self):
        with mock.patch("urllib.request.urlopen", lambda r, timeout=0: fake_response("ok")):
            self.assertEqual(openai_compatible_chat("ollama")([], "s"), "ok")

    def test_http_429_is_retryable_400_is_not(self):
        def boom(code):
            def urlopen(req, timeout=0):
                raise urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b"err"))
            return urlopen
        chat = openai_compatible_chat("ollama")
        with mock.patch("urllib.request.urlopen", boom(429)):
            with self.assertRaises(ProviderError) as c:
                chat([], "s")
            self.assertTrue(c.exception.retryable)
        with mock.patch("urllib.request.urlopen", boom(400)):
            with self.assertRaises(ProviderError) as c:
                chat([], "s")
            self.assertFalse(c.exception.retryable)

    def test_fallback_skips_retries_on_fatal_but_tries_next_provider(self):
        def limited(m, s):
            raise ProviderError("429", True)

        def fatal(m, s):
            raise ProviderError("400", False)
        with mock.patch("time.sleep"):
            self.assertEqual(fallback_chat([limited, lambda m, s: "ok"])([], "s"), "ok")
            calls = []

            def fatal_counted(m, s):
                calls.append(1)
                raise ProviderError("401", False)
            self.assertEqual(fallback_chat([fatal_counted, lambda m, s: "ok"], retries_per_chat=3)([], "s"), "ok")
            self.assertEqual(len(calls), 1)  # no retry on a non-retryable error
            with self.assertRaises(RuntimeError):
                fallback_chat([fatal, fatal])([], "s")
            with self.assertRaises(RuntimeError):
                fallback_chat([limited, limited])([], "s")

    def test_build_chat_unknown(self):
        with self.assertRaises(ValueError):
            build_chat("nope")


if __name__ == "__main__":
    unittest.main()
