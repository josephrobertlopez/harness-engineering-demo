"""Stub claude that returns a veto (confirmed - use this for majority of judges)."""
import sys

sys.stdout.write(r"""{
  "stop_reason": "end_turn",
  "result": "{\"verdict\":\"veto\",\"file\":\"src/foo.py\",\"line\":\"42\",\"claim\":\"function missing\"}"
}
""")
