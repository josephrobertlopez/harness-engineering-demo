---
name: instructions
description: Output conventions — timestamp format and rounding mode.
---

1. Timestamps are ISO-8601: replace the space separator with `T` and append
   a trailing Z. `2026-03-04 11:02:33` becomes `2026-03-04T11:02:33Z`. Do
   not shift the clock or add fractional seconds — only reshape the string.

2. Amounts round half-to-even at two decimals, not half-up. When the dropped
   part is exactly half, round the last kept digit to the nearest even
   digit: `2.345` becomes `2.34`, `2.355` becomes `2.36`.
