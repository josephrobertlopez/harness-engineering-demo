# Tasks: Help centre chatbot (SUP-88)

## 1. Infrastructure and session management

- [x] 1.1 Implement terminal I/O for `python chatbot.py` (read from stdin, write to stdout)
- [x] 1.2 Implement session initialization and cleanup (Ctrl-D/Ctrl-Z handling)
- [x] 1.3 Implement in-memory session state (no persistence to disk)
- [x] 1.4 Test scenario: Session starts cleanly when chatbot is invoked
- [x] 1.5 Test scenario: Session ends and state is discarded on Ctrl-D
- [x] 1.6 Test scenario: Session ends and state is discarded on Ctrl-Z
- [x] 1.7 Test scenario: New session has no access to prior session data

## 2. FAQ matching and answering

- [x] 2.1 Load FAQ data from `faq.md` into a queryable data structure
- [x] 2.2 Implement FAQ matching logic (method: non-goal, developer discretion)
- [x] 2.3 Integrate Claude API with `claude-sonnet-5` model
- [x] 2.4 Implement API key loading from `ANTHROPIC_API_KEY` environment variable
- [x] 2.5 Set `max_tokens` to 512 and omit `temperature` parameter
- [x] 2.6 Implement context window management (last 6 messages, sliding window)
- [x] 2.7 Test scenario: FAQ-matched question invokes Claude and returns response
- [x] 2.8 Test scenario: Response is based exclusively on matched FAQ entry
- [x] 2.9 Test scenario: Context window includes last 6 messages from session
- [x] 2.10 Test scenario: Messages older than 6 are dropped from context
- [x] 2.11 Test scenario: Context is cleared when session ends

## 3. Out-of-FAQ escalation

- [x] 3.1 Implement escalation detection for questions outside FAQ
- [x] 3.2 Return exact escalation message: `I don't know that one yet — I've passed your question to a human.`
- [x] 3.3 Mark escalated turns internally (no Claude API call)
- [x] 3.4 Test scenario: Non-FAQ question returns escalation message
- [x] 3.5 Test scenario: Escalated turn does not call Claude API
- [x] 3.6 Test scenario: Escalated turn is marked internally

## 4. Safety: Card number detection

- [x] 4.1 Implement Luhn check algorithm for card number validation
- [x] 4.2 Implement card number detection (13-19 digits, optional spaces/dashes)
- [x] 4.3 Return exact refusal message: `I can't help with passwords or card numbers here. Please contact support@example.com.`
- [x] 4.4 Ensure detected card numbers are not stored in conversation memory
- [x] 4.5 Do not call Claude when card number is detected
- [x] 4.6 Test scenario: Card number message is detected and refused
- [x] 4.7 Test scenario: Luhn-validated card numbers are detected
- [x] 4.8 Test scenario: Invalid card numbers (failing Luhn) are not detected
- [x] 4.9 Test scenario: Card numbers with spaces/dashes are detected
- [x] 4.10 Test scenario: Detected card numbers are not stored in memory
- [x] 4.11 Test scenario: Claude is not called when card is detected

## 5. Safety: Password detection

- [x] 5.1 Implement password pattern matching (case-insensitive)
- [x] 5.2 Detect patterns: "password is", "password:", "pwd=" followed by word with digit/symbol
- [x] 5.3 Handle single and multiple whitespace between pattern and password
- [x] 5.4 Return exact refusal message: `I can't help with passwords or card numbers here. Please contact support@example.com.`
- [x] 5.5 Ensure detected passwords are not stored in conversation memory
- [x] 5.6 Do not call Claude when password is detected
- [x] 5.7 Test scenario: Password message is detected and refused
- [x] 5.8 Test scenario: Case-insensitive password pattern matching works
- [x] 5.9 Test scenario: Whitespace variations in pattern are handled
- [x] 5.10 Test scenario: Detected passwords are not stored in memory
- [x] 5.11 Test scenario: Claude is not called when password is detected

## 6. Integration and end-to-end

- [x] 6.1 Verify API key is read from `ANTHROPIC_API_KEY`, never from source
- [x] 6.2 End-to-end test: FAQ question answered, non-FAQ escalated, safety detected
- [x] 6.3 Verify exact message strings for escalation and refusal
- [x] 6.4 Verify model id is exactly `claude-sonnet-5` with max_tokens=512, no temperature
