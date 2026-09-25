"""FAQ loading and matching."""
import os
import re


class FAQMatcher:
    """Matches user questions to FAQ entries and returns answers."""

    def __init__(self):
        """Initialize the FAQ matcher by loading FAQ from faq.md."""
        self.faqs = self._load_faq()

    def _load_faq(self):
        """Load FAQ entries from faq.md file.

        Returns:
            list of dict with keys: title, keywords, answer
        """
        faq_path = os.path.join(os.path.dirname(__file__), "..", "faq.md")

        if not os.path.exists(faq_path):
            return []

        faqs = []
        with open(faq_path, "r") as f:
            content = f.read()

        # Split by ## (FAQ headers)
        entries = re.split(r"^## ", content, flags=re.MULTILINE)[1:]  # Skip the initial markdown header

        for entry in entries:
            lines = entry.strip().split("\n")
            if not lines:
                continue

            title = lines[0]
            keywords_line = ""
            answer_lines = []

            for i, line in enumerate(lines[1:], 1):
                if line.startswith("keywords:"):
                    keywords_line = line
                elif line and not keywords_line:
                    # Haven't found keywords yet, skip
                    continue
                elif keywords_line:
                    # This is part of the answer
                    answer_lines.append(line)

            # Extract keywords
            keywords = []
            if keywords_line:
                keyword_part = keywords_line.replace("keywords:", "").strip()
                keywords = [k.strip() for k in keyword_part.split(",")]

            # Build answer
            answer = "\n".join(answer_lines).strip()

            if title and keywords and answer:
                faqs.append({
                    "title": title,
                    "keywords": keywords,
                    "answer": answer
                })

        return faqs

    def find_match(self, question):
        """Find a matching FAQ entry for the question.

        Uses simple keyword matching to determine if a question relates to an FAQ topic.

        Args:
            question: User's question string

        Returns:
            str: FAQ answer if a match is found, None otherwise
        """
        question_lower = question.lower()

        for faq in self.faqs:
            for keyword in faq["keywords"]:
                if keyword.lower() in question_lower:
                    return faq["answer"]

        return None
