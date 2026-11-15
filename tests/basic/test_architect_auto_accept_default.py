"""Regression tests for issue #5748.

`--auto-accept-architect` defaulted to True, so the architect coder handed its
proposed edits straight to the editor coder with no "Edit the files?" prompt.
These tests pin the safe default: architect edits require confirmation unless
the user explicitly opts back in with `--auto-accept-architect`.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from aider.args import get_parser
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.utils import GitTemporaryDirectory


class TestArchitectAutoAcceptDefault(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def default_auto_accept_flag(self):
        parser = get_parser([], None)
        return parser.parse_known_args([])[0].auto_accept_architect

    def make_architect_coder(self, io, auto_accept_architect):
        with GitTemporaryDirectory():
            return Coder.create(
                self.GPT35,
                "architect",
                io,
                auto_accept_architect=auto_accept_architect,
            )

    def test_cli_default_is_no_auto_accept(self):
        """The CLI default must not auto-accept architect edits."""
        self.assertFalse(self.default_auto_accept_flag())

    def test_explicit_flag_still_enables_auto_accept(self):
        """Escape hatch: --auto-accept-architect restores the fast path."""
        parser = get_parser([], None)
        args = parser.parse_known_args(["--auto-accept-architect"])[0]
        self.assertTrue(args.auto_accept_architect)

    def test_env_var_can_disable_auto_accept(self):
        """AIDER_AUTO_ACCEPT_ARCHITECT=false keeps working after the flip."""
        with patch.dict(os.environ, {"AIDER_AUTO_ACCEPT_ARCHITECT": "false"}):
            parser = get_parser([], None)
            args = parser.parse_known_args([])[0]
        self.assertFalse(args.auto_accept_architect)

    def test_architect_prompts_before_applying_edits_by_default(self):
        """With the shipped default, reply_completed must ask before editing."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=None, pretty=False)
            io.confirm_ask = MagicMock(return_value=True)
            coder = self.make_architect_coder(io, self.default_auto_accept_flag())

            mock_editor = MagicMock()
            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                coder.partial_response_content = "Make these changes to the code"
                coder.reply_completed()

            io.confirm_ask.assert_called_once_with("Edit the files?")
            mock_editor.run.assert_called_once()

    def test_architect_skips_edits_when_user_declines(self):
        """Answering no must stop the editor coder from running."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=None, pretty=False)
            io.confirm_ask = MagicMock(return_value=False)
            coder = self.make_architect_coder(io, self.default_auto_accept_flag())

            mock_editor = MagicMock()
            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                coder.partial_response_content = "Make these changes to the code"
                coder.reply_completed()

            io.confirm_ask.assert_called_once_with("Edit the files?")
            mock_editor.run.assert_not_called()

    def test_unattended_runs_do_not_stall(self):
        """-y / --yes-always still applies architect edits with no prompt."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True, pretty=False)
            coder = self.make_architect_coder(io, self.default_auto_accept_flag())

            mock_editor = MagicMock()
            with patch("builtins.input", side_effect=AssertionError("must not prompt")):
                with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                    coder.partial_response_content = "Make these changes to the code"
                    coder.reply_completed()

            mock_editor.run.assert_called_once()

    def test_architect_auto_accepts_when_opted_in(self):
        """Explicit opt-in keeps the old no-prompt behaviour."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=None, pretty=False)
            io.confirm_ask = MagicMock(return_value=True)
            coder = self.make_architect_coder(io, True)

            mock_editor = MagicMock()
            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                coder.partial_response_content = "Make these changes to the code"
                coder.reply_completed()

            io.confirm_ask.assert_not_called()
            mock_editor.run.assert_called_once()


if __name__ == "__main__":
    os.environ.setdefault("AIDER_ANALYTICS", "false")
    unittest.main()
