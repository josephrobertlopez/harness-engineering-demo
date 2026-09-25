"""Claude API integration handler using LangChain."""
import os
from langchain_anthropic import ChatAnthropic


class ClaudeHandler:
    """Handles communication with the Claude API via LangChain."""

    def __init__(self):
        """Initialize the Claude handler with API key from environment."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = ChatAnthropic(
            model="claude-sonnet-5",
            max_tokens=512,
            api_key=api_key
        )

    def generate_response(self, question, faq_answer, context_messages):
        """Generate a response using Claude.

        Args:
            question: User's question
            faq_answer: The FAQ answer to provide context
            context_messages: List of prior messages in the conversation

        Returns:
            str: The response text from Claude
        """
        from langchain_core.messages import HumanMessage, AIMessage

        # Build the messages list with context and the current question
        messages = []

        # Add context messages
        for msg in context_messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # Add the current question
        user_message = HumanMessage(
            content=f"FAQ Entry:\n{faq_answer}\n\nQuestion:\n{question}"
        )
        messages.append(user_message)

        # Call Claude via LangChain
        response = self.client.invoke(messages)

        # Extract and return the response text
        return response.content
