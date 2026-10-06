"""Stub claude that returns invalid JSON."""
import sys

sys.stdout.write(r"""{
  "stop_reason": "end_turn",
  "result": "NOT VALID JSON {{"
}
""")
