"""Stub claude that returns truncated output with stop_reason max_tokens."""
import sys

sys.stdout.write(r"""{
  "stop_reason": "max_tokens",
  "result": "{\"verdict\":\"pass\",\"file\":\"src/foo.py\",\"line\":\"42\",\"claim\":\"function exists\""
}
""")
