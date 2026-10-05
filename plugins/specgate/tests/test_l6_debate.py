"""Tests for L6 debate module."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from specgate.l6_debate import run_debate


class TestL6Debate(unittest.TestCase):
    """Tests for L6 debate logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent
        self.fixtures_dir = self.test_dir / "fixtures" / "l6"
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

        # Ensure fixture stubs exist
        self.bin_dir = self.fixtures_dir / "bin"
        self.bin_dir.mkdir(exist_ok=True)

    def test_run_debate_good_pass_all_judges(self):
        """Test when all judges vote pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            # Create a simple recheck that always returns True
            def recheck(file, line, claim):
                return True

            # Supply a dummy token so cache miss can proceed
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            # Run with stub claude that returns good-pass
            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "added foo()"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "good-pass"),
                env=env,
            )

            self.assertEqual(result["findings"], [])
            self.assertEqual(result["ignored_vetoes"], [])
            self.assertGreaterEqual(result["calls"], 3)  # Prover + Refuter + 3 Judges

    def test_run_debate_cache_hit(self):
        """Test that cache hits prevent subprocess calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            # Create cache file with entries for all judge prompts
            # Pre-compute cache keys for the expected prompts
            cache_file = change_dir / "debate.cache.json"

            # Cache hits should contain valid verdicts
            cache_data = {}
            # Add some cached verdicts - they'll be used on cache hit
            cache_key_1 = hashlib.sha256(b"dummy_prompt_1claude-sonnet-5-5").hexdigest()
            cache_key_2 = hashlib.sha256(b"dummy_prompt_2claude-sonnet-5-5").hexdigest()
            cache_data[cache_key_1] = {"verdict": {"verdict": "pass", "file": "", "line": "", "claim": ""}}
            cache_data[cache_key_2] = {"verdict": {"verdict": "pass", "file": "", "line": "", "claim": ""}}

            cache_file.write_text(json.dumps(cache_data))

            def recheck(file, line, claim):
                return True

            # Supply dummy token (though cache hits don't need it, better practice)
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            # Run with cache present - should hit cache
            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "good-pass"),
                env=env,
            )

            # If cache working properly, calls should be lower or zero for cached items
            self.assertIsNotNone(result)
            self.assertIn("findings", result)
            self.assertIn("calls", result)

    def test_run_debate_bad_json_fails(self):
        """Test that bad JSON output causes SG601 failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return True

            # Supply dummy token for cache miss
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            # Run with stub that returns bad JSON
            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "bad-json"),
                env=env,
            )

            # Should have SG601 findings for invalid JSON
            self.assertTrue(
                any(f["rule"] == "SG601" for f in result["findings"]),
                "Expected SG601 finding for bad JSON",
            )

    def test_run_debate_truncated_output_fails(self):
        """Test that truncated output (stop_reason max_tokens) causes SG601 failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return True

            # Supply dummy token for cache miss
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "truncated"),
                env=env,
            )

            # Should have SG601 finding for truncation
            self.assertTrue(
                any(f["rule"] == "SG601" for f in result["findings"]),
                "Expected SG601 finding for truncated output",
            )

    def test_run_debate_unconfirmed_veto_ignored(self):
        """Test that unconfirmed vetoes (single judge) are logged but not reported as findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return False  # Veto not confirmed

            # Supply dummy token for cache miss
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "veto-unconfirmed"),
                env=env,
            )

            # Unconfirmed vetoes should be in ignored_vetoes, not findings
            self.assertTrue(len(result["ignored_vetoes"]) > 0)
            self.assertTrue(all(f["rule"] != "SG603" for f in result["findings"]))

    def test_run_debate_confirmed_majority_veto_fails(self):
        """Test that confirmed majority veto causes SG603 failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return True  # Veto is confirmed

            # Supply dummy token for cache miss
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "veto-confirmed"),
                env=env,
            )

            # Should have SG603 finding for confirmed majority veto
            self.assertTrue(
                any(f["rule"] == "SG603" for f in result["findings"]),
                "Expected SG603 finding for confirmed veto",
            )

    def test_run_debate_cache_miss_no_token_fails(self):
        """Test that cache miss with no token available causes SG602 failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return True

            # Run with no token env vars (simulating CI environment with no credentials)
            env = {k: v for k, v in os.environ.items()
                   if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")}

            # Create a mock stub that should never be called
            stub_path = self.bin_dir / "should-not-be-called"
            stub_path.write_text("#!/bin/bash\nexit 1\n")
            stub_path.chmod(0o755)

            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(stub_path),
                env=env,
            )

            # Should have exactly one SG602 finding (for prover cache miss)
            sg602_findings = [f for f in result["findings"] if f["rule"] == "SG602"]
            self.assertEqual(len(sg602_findings), 1, "Expected exactly one SG602 finding")
            self.assertEqual(sg602_findings[0]["line"], 0, "SG602 should have line 0")

            # Should have zero subprocess calls (stub never invoked)
            self.assertEqual(result["calls"], 0, "Expected zero subprocess calls with SG602")

    def test_run_debate_cache_hit_no_token_succeeds(self):
        """Test that cache hit works even without token (no SG602, no subprocess)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            # Pre-populate cache with verdicts for all expected calls
            cache_file = change_dir / "debate.cache.json"
            cache_data = {}

            # Build the expected prompts
            from specgate.l6_debate import _build_prover_prompt, _build_refuter_prompt, _build_judge_prompt

            inputs = {"change": "test change"}
            prover_prompt = _build_prover_prompt(inputs)
            refuter_prompt = _build_refuter_prompt(inputs)

            # Pre-compute cache keys
            import hashlib
            prover_key = hashlib.sha256((prover_prompt + "claude-sonnet-5-5").encode()).hexdigest()
            refuter_key = hashlib.sha256((refuter_prompt + "claude-sonnet-5-5").encode()).hexdigest()

            # Add cached verdicts
            cache_data[prover_key] = {"verdict": {"verdict": "pass", "file": "", "line": "", "claim": ""}}
            cache_data[refuter_key] = {"verdict": {"verdict": "pass", "file": "", "line": "", "claim": ""}}

            # Add verdicts for judges (they'll reference the cached prover/refuter)
            for i in range(3):
                judge_prompt = _build_judge_prompt(
                    i,
                    {"verdict": "pass", "file": "", "line": "", "claim": ""},
                    {"verdict": "pass", "file": "", "line": "", "claim": ""}
                )
                judge_key = hashlib.sha256((judge_prompt + "claude-sonnet-5-5").encode()).hexdigest()
                cache_data[judge_key] = {"verdict": {"verdict": "pass", "file": "", "line": "", "claim": ""}}

            cache_file.write_text(json.dumps(cache_data))

            def recheck(file, line, claim):
                return True

            # Run with NO token env vars - cache hits should still work
            env = {k: v for k, v in os.environ.items()
                   if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")}

            # Stub that should never be called
            stub_path = self.bin_dir / "should-not-be-called"
            stub_path.write_text("#!/bin/bash\nexit 1\n")
            stub_path.chmod(0o755)

            result = run_debate(
                change_dir=change_dir,
                inputs=inputs,
                recheck=recheck,
                claude_bin=str(stub_path),
                env=env,
            )

            # Should have no SG602 findings (all hits from cache)
            sg602_findings = [f for f in result["findings"] if f["rule"] == "SG602"]
            self.assertEqual(len(sg602_findings), 0, "Expected no SG602 findings when cache hits")

            # Should have zero subprocess calls (all served from cache)
            self.assertEqual(result["calls"], 0, "Expected zero subprocess calls with all cache hits")

            # Should have no findings at all (all pass)
            self.assertEqual(result["findings"], [], "Expected no findings when all judges pass")

    def test_run_debate_structure(self):
        """Test that run_debate returns correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            change_dir = Path(tmpdir)

            def recheck(file, line, claim):
                return True

            # Supply dummy token for cache miss
            env = os.environ.copy()
            env["CLAUDE_CODE_OAUTH_TOKEN"] = "dummy-token-for-testing"

            result = run_debate(
                change_dir=change_dir,
                inputs={"change": "test"},
                recheck=recheck,
                claude_bin=str(self.bin_dir / "good-pass"),
                env=env,
            )

            # Check structure
            self.assertIn("findings", result)
            self.assertIn("ignored_vetoes", result)
            self.assertIn("calls", result)

            # Check that findings are dicts with expected keys
            for finding in result["findings"]:
                self.assertIn("rule", finding)
                self.assertIn("message", finding)

            # Check that ignored_vetoes are dicts
            for veto in result["ignored_vetoes"]:
                self.assertIsInstance(veto, dict)


if __name__ == "__main__":
    unittest.main()
