# Tasks

## 1. Policy (stdlib)

- [x] 1.1 Parse `faq.md` into entries with keywords
- [x] 1.2 Keyword retrieval, most hits wins, ties to the first entry
- [x] 1.3 Card-number (Luhn) and shared-password (digit or symbol) detection
- [x] 1.4 Six-message window
- [x] 1.5 Model parameters: `claude-sonnet-5`, `max_tokens=512`, no temperature

## 2. LangChain wiring

- [x] 2.1 Prompt: system + FAQ entry, history placeholder, question
- [x] 2.2 `HelpBot.reply`: refuse, escalate, or invoke the chain
- [x] 2.3 Per-session `InMemoryChatMessageHistory`; refused turns never stored
- [x] 2.4 `make_model()` builds `ChatAnthropic` from the policy parameters

## 3. Terminal

- [x] 3.1 `python chatbot.py` reads stdin until end-of-input

## 4. Verification

- [x] 4.1 One test per scenario, each naming its scenario
