"""The 20 answers on a real Magic 8 Ball, and the three groups they fall into.

The ball never says anything else. Each group is listed from the most sure phrase to the least sure,
so how sure the model is can pick the phrase.
"""
from __future__ import annotations

CATEGORIES = ("yes", "maybe", "no")

ANSWERS: dict[str, list[str]] = {
    "yes": [
        "It is certain",
        "Without a doubt",
        "Yes definitely",
        "It is decidedly so",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yes",
        "Signs point to yes",
    ],
    "maybe": [
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again",
    ],
    "no": [
        "My reply is no",
        "Very doubtful",
        "My sources say no",
        "Don't count on it",
        "Outlook not so good",
    ],
}


def category_of(answer: str) -> str:
    for cat, phrases in ANSWERS.items():
        if answer in phrases:
            return cat
    raise KeyError(answer)


def all_answers() -> list[dict]:
    return [{"answer": a, "category": c, "strength": i + 1} for c, ps in ANSWERS.items() for i, a in enumerate(ps)]
