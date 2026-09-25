"""Session management for the chatbot."""


class Session:
    """Manages a single chatbot session with in-memory message history."""

    def __init__(self):
        """Initialize a new session with empty message history."""
        self.messages = []
        self.closed = False

    def add_message(self, role, content):
        """Add a message to the session history.

        Args:
            role: "user" or "assistant"
            content: Message content string
        """
        if not self.closed:
            self.messages.append({"role": role, "content": content})

    def get_context(self):
        """Get the last 6 messages (3 exchanges) for Claude context.

        Returns:
            List of up to 6 most recent messages
        """
        return self.messages[-6:] if len(self.messages) > 0 else []

    def close(self):
        """Close the session and discard all state."""
        self.messages.clear()
        self.closed = True
