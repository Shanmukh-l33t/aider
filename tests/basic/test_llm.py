import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLazyLiteLLM(unittest.TestCase):
    def lazy_load_in_subprocess(self, log_level):
        """Trigger the lazy litellm import in a fresh process.

        litellm evaluates LITELLM_LOG at import time, so the crash only
        reproduces on a cold import -- hence the subprocess.
        """
        env = os.environ.copy()
        env["LITELLM_LOG"] = log_level
        env["AIDER_ANALYTICS"] = "false"
        return subprocess.run(
            [sys.executable, "-c", "from aider.llm import litellm; litellm._load_litellm()"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_load_litellm_tolerates_trailing_space_in_LITELLM_LOG(self):
        # issue #5971: LITELLM_LOG="DEBUG " crashed aider startup with
        # AttributeError: module 'logging' has no attribute 'DEBUG '
        res = self.lazy_load_in_subprocess("DEBUG ")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertNotIn("AttributeError", res.stderr)

    def test_load_litellm_tolerates_whitespace_only_LITELLM_LOG(self):
        res = self.lazy_load_in_subprocess("   ")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertNotIn("AttributeError", res.stderr)
