# SUP-88 Interview — Help centre chatbot (LangChain)

## Success criteria & behavior

### Q1. Where will customers access this chatbot?
Is it embedded in the help centre website, a Slack app, a dedicated page, or somewhere else? This shapes the entire interaction model.

A: Customers access the chatbot via terminal chat by running `python chatbot.py`. Each run is one session and ends cleanly on end-of-input (Ctrl-D or Ctrl-Z). The web widget is a different ticket and out of scope.

### Q2. What should the chatbot do when asked something outside the FAQ?
The ticket mentions being "smart about what it doesn't know." Does that mean: refuse to answer, try to answer anyway from general knowledge, or redirect the customer to open a support ticket?

A: When asked something outside the FAQ, the bot replies with exactly `I don't know that one yet — I've passed your question to a human.` and marks the turn as escalated. The model is not called for that turn.

### Q3. What is the target accuracy or success rate for FAQ questions?
How do we measure whether "answers questions" is working? Should we aim for 95% of FAQ-related queries being answered correctly, or something else?

A: No decision - treat it as a non-goal.

### Q4. When you say "not say anything bad," what specific content should the chatbot refuse?
Should it refuse: misinformation about the product, harmful advice, illegal content, personal attacks, or all of the above? Are there topics it should never engage with?

A: The chatbot refuses messages containing card numbers (13–19 digits, spaces or dashes allowed, that pass the Luhn check) or passwords (detected by "password is", "password:", or "pwd=" followed by a word containing a digit or symbol). The refusal response is exactly `I can't help with passwords or card numbers here. Please contact support@example.com.` The refused message is not kept in memory.

### Q5. What exactly should the chatbot remember, and for how long?
Should memory persist: only within a single conversation session, across sessions for logged-in users, indefinitely? And what should it remember — just the conversation history, or also inferences about the user's situation?

A: Per session, the last 6 messages (three exchanges) are sent to the model with each new question; older messages are dropped. Sessions are isolated from each other. Nothing is written to disk — a restart forgets everything, and that is fine.

## Routing & retrieval

### Q6. How should the chatbot decide whether a question is FAQ-related or not?
Should it: keyword-match the FAQ first and only escalate if no keywords match, ask Claude to decide, or use some other logic? This determines the escalation flow.

A: No decision - treat it as a non-goal. The document specifies that the bot must find a matching FAQ entry and answer from it, and that unmatched questions trigger escalation with a standard message. The mechanism for determining whether a question matches an entry is not defined.

### Q7. What system prompt should Claude receive to guide its behavior?
Should it be told "you are a support assistant with access to these 5 FAQs, answer only from them," or something different? What constraints or style guidance does Claude need?

A: No decision - treat it as a non-goal.

## Error handling

### Q8. What should happen if the Claude API fails, times out, or returns an error?
Should the chatbot: escalate the turn as if it were out-of-FAQ, tell the user there's a temporary issue, or retry?

A: No decision - treat it as a non-goal.

## Messaging & clarity

### Q9. Should the chatbot identify itself as AI or mention that it's using Claude?
Should it say something like "I'm an AI assistant here to help" or just answer directly without attribution?

A: No decision - treat it as a non-goal.

### Q10. When answering an FAQ question, should the chatbot reference which FAQ section it came from?
Or should it just provide the answer without attribution to the FAQ?

A: No decision - treat it as a non-goal.

## Implementation specifics

### Q11. Which Claude model should the chatbot use?
Should it be Claude 3.5 Sonnet, Opus, or a specific version? This affects capability and cost.

A: `claude-sonnet-5` (exactly that id, no date suffix), with `max_tokens` **512**. Do not set `temperature` — the API rejects it for this model with a 400.

### Q12. When answering an FAQ question, what information about the FAQ is provided to Claude?
Should the prompt include: the full FAQ text, just the matching FAQ entry, or just keywords? How should it be formatted?

A: No decision — treat it as a non-goal.

### Q13. How should the last 6 messages (three exchanges) be formatted when sent to Claude?
Should they be in `{"role": "user"|"assistant", "content": "..."}` format, plain text, or some other structure?

A: No decision — treat it as a non-goal.

### Q14. What is the terminal interaction model — prompt symbol, line breaks, etc.?
Should the user see `> ` before typing, or just type directly? Should there be blank lines between turns?

A: No decision — treat it as a non-goal.

### Q15. How will this chatbot be tested or verified to meet the acceptance criteria?
Are there specific test scenarios, or is manual verification expected?

A: No decision — treat it as a non-goal.

## Final edge cases

### Q16. What should happen if the user submits an empty input (blank line or whitespace only)?
Should it: prompt again, escalate, or pass it to Claude?

A: No decision - treat it as a non-goal.

### Q17. When counting the "last 6 messages" for context, do escalated turns (no-model calls) count toward that limit?
For example, if the last 3 turns were escalations, are those 3 messages still in the 6-message window?

A: No decision - treat it as a non-goal.

### Q18. Should the chatbot display/print the conversation history to the user, or only show its responses?
For example, should the user see their own prior questions printed back, or just the bot's answers?

A: No decision - treat it as a non-goal.

## Judge-flagged questions

### Q19. When a turn is marked as escalated (for out-of-FAQ questions), what observable behavior or state change results from this marking?
Is it purely internal, or does it affect metrics, logs, visible output, or any other observable aspect of the chatbot's behavior?

A: The observable behavior is that the bot replies with exactly `I don't know that one yet — I've passed your question to a human.` and does not call the model for that turn. Whether marking the turn as escalated results in additional observable effects such as logging, metrics, or alerts is not decided — treat it as a non-goal.

### Q20. Where should the Claude API key come from?
Should it be an environment variable, a config file, passed as a command-line argument, read from a secrets manager, or sourced some other way?

A: The API key comes from the environment variable `ANTHROPIC_API_KEY`, never from source.
