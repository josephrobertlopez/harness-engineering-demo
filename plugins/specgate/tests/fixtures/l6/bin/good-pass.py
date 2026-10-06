"""Stub claude that returns a good pass response."""
import sys

sys.stdout.write(r"""{
  "stop_reason": "end_turn",
  "result": "{\"verdict\":\"pass\",\"file\":\"\",\"line\":\"\",\"claim\":\"\"}"
}
""")
