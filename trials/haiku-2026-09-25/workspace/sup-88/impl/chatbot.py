"""Main chatbot implementation."""
import sys
from langchain_core.messages import BaseMessage
from session import Session
from safety import SafetyDetector
from faq import FAQMatcher
from claude_handler import ClaudeHandler


class Chatbot:
    """Main chatbot that coordinates all components."""

    def __init__(self):
        """Initialize the chatbot."""
        self.session = Session()
        self.detector = SafetyDetector()
        self.faq = FAQMatcher()
        self.claude = ClaudeHandler()
        self.escalated_turns = []

    def process_message(self, user_input):
        """Process a user message and return a response.

        Args:
            user_input: The user's message

        Returns:
            str: The chatbot's response
        """
        # Check for sensitive data
        safety_result = self.detector.check_message(user_input)
        if safety_result["contains_sensitive"]:
            return "I can't help with passwords or card numbers here. Please contact support@example.com."

        # Store the user message in session
        self.session.add_message("user", user_input)

        # Try to match to FAQ
        faq_answer = self.faq.find_match(user_input)

        if faq_answer is None:
            # No FAQ match - escalate
            response = "I don't know that one yet — I've passed your question to a human."
            self.escalated_turns.append(len(self.session.messages))
            # Mark the turn as escalated (internal flag)
            # Do not call Claude for this turn
            return response

        # FAQ match found - call Claude
        context = self.session.get_context()[:-1]  # Exclude the current user message we just added
        response = self.claude.generate_response(user_input, faq_answer, context)

        # Store the response in session
        self.session.add_message("assistant", response)

        return response

    def run(self):
        """Run the chatbot in interactive mode."""
        print("Help Centre Chatbot")
        print("Type your question or press Ctrl-D to exit\n")

        try:
            while True:
                try:
                    user_input = input("> ").strip()
                    if not user_input:
                        continue

                    response = self.process_message(user_input)
                    print(f"\n{response}\n")
                except EOFError:
                    # Ctrl-D pressed
                    print("\nGoodbye!")
                    self.session.close()
                    break
        except KeyboardInterrupt:
            # Ctrl-C pressed
            print("\nGoodbye!")
            self.session.close()


def main():
    """Entry point for the chatbot CLI."""
    chatbot = Chatbot()
    chatbot.run()


if __name__ == "__main__":
    main()
