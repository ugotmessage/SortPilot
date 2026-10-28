import unittest
from ai_provider import validate_ai, DEFAULT_URLS


class AIProviderTests(unittest.TestCase):
    def test_valid_providers(self):
        for provider in ("ollama", "openai", "gemini", "compatible"):
            validate_ai(provider, DEFAULT_URLS[provider], "test-model")
        validate_ai("off", "", "")

    def test_reject_remote_http(self):
        with self.assertRaises(ValueError):
            validate_ai("compatible", "http://example.com/v1", "model")

    def test_reject_credentials_in_url(self):
        with self.assertRaises(ValueError):
            validate_ai("openai", "https://user:secret@example.com/v1", "model")

    def test_reject_missing_model(self):
        with self.assertRaises(ValueError):
            validate_ai("ollama", "http://127.0.0.1:11434", "")
