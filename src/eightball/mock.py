"""A stand-in model for tests and for trying the plumbing without Ollama. It knows nothing:
it reacts to a few words so the tests are predictable. Its answers say nothing about real models."""
from __future__ import annotations

FUTURE = ("will ", "tomorrow", "next ", "going to")


class MockBackend:
    name = "mock"

    def scores(self, question: str, order: list[str]) -> list[float]:
        q = question.lower()
        if "not " in q or "false" in q:
            pick = "no"
        elif any(w in q for w in FUTURE) or not q.strip().endswith("?"):
            pick = "maybe"
        else:
            pick = "yes"
        # a mild lean towards the first-listed option, so tests can see the shuffling cancel it
        return [(4.0 if k == pick else 0.0) + (0.5 if i == 0 else 0.0) for i, k in enumerate(order)]

    def plain(self, question: str) -> str:
        s = self.scores(question, ["yes", "no", "maybe"])
        return ("yes", "no", "maybe")[s.index(max(s))]
