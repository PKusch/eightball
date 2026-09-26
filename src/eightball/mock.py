"""A stand-in model for tests and for trying the plumbing without Ollama. It knows nothing:
it reacts to a few words so the tests are predictable. Its answers say nothing about real models."""
from __future__ import annotations

FUTURE = ("will ", "tomorrow", "next ", "going to")


class MockBackend:
    name = "mock"

    def scores(self, question: str, order: list[str], text: str | None = None) -> list[float]:
        q = question.lower()
        if text is not None:  # text mode: a stand-in that reacts to marker words in the text
            tl = text.lower()
            pick = "maybe" if "unknown" in tl else "no" if " no " in f" {tl} " else "yes"
        elif "not " in q or "false" in q:
            pick = "no"
        elif any(w in q for w in FUTURE) or not q.strip().endswith("?"):
            pick = "maybe"
        else:
            pick = "yes"
        # a mild lean towards the first-listed option, so tests can see the shuffling cancel it
        return [(4.0 if k == pick else 0.0) + (0.5 if i == 0 else 0.0) for i, k in enumerate(order)]

    def plain(self, question: str, text: str | None = None) -> str:
        s = self.scores(question, ["yes", "no", "maybe"], text)
        return ("yes", "no", "maybe")[s.index(max(s))]
