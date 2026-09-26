"""Talks to a local Ollama model. It never asks the model to write an answer; it reads the model's
odds for the letter it would pick first (A, B or C), which is one short call and gives real numbers."""
from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.request

KEYS = ("yes", "no", "maybe")

OPTION_TEXT = {
    "yes": "Yes: the statement is true, or it will happen.",
    "no": "No: the statement is false, or it will not happen.",
    "maybe": "Cannot be known: it depends on the future, on a private matter, on taste, or it is not a yes/no question.",
}
LETTERS = "ABC"
TOP_LOGPROBS = 20
FLOOR_MARGIN = 5.0  # a letter the model did not rank gets (lowest ranked score - this)


class BackendError(RuntimeError):
    pass


TEXT_OPTION_TEXT = {
    "yes": "Yes: the text says so.",
    "no": "No: the text says the opposite.",
    "maybe": "Not stated: the text does not say.",
}


def build_text_prompt(text: str, question: str, order: list[str]) -> str:
    lines = [
        "You are the spirit inside a Magic 8 Ball. Read the text, then answer the question about it using "
        "only what the text says. Reply with the letter of exactly one option.",
        "",
        "TEXT:",
        text.strip(),
        "",
        "QUESTION:",
        question.strip(),
        "",
        "OPTIONS:",
    ]
    lines += [f"{LETTERS[i]}. {TEXT_OPTION_TEXT[k]}" for i, k in enumerate(order)]
    lines += ["", "Reply with the letter of your chosen option only, nothing else.", "ANSWER:"]
    return "\n".join(lines)


def build_plain_text_prompt(text: str, question: str) -> str:
    return (
        "Read the text, then answer the question about it using only what the text says. Answer with exactly one word: "
        "YES if the text says so, NO if the text says the opposite, MAYBE if the text does not say.\n\n"
        f"TEXT:\n{text.strip()}\n\nQUESTION:\n{question.strip()}\n\nANSWER:"
    )


def build_prompt(question: str, order: list[str]) -> str:
    lines = [
        "You are the spirit inside a Magic 8 Ball. A person asks you a question. "
        "Decide which kind of answer it deserves and reply with the letter of exactly one option.",
        "",
        "QUESTION:",
        question.strip(),
        "",
        "OPTIONS:",
    ]
    lines += [f"{LETTERS[i]}. {OPTION_TEXT[k]}" for i, k in enumerate(order)]
    lines += ["", "Reply with the letter of your chosen option only, nothing else.", "ANSWER:"]
    return "\n".join(lines)


def build_plain_prompt(question: str) -> str:
    return (
        "You are the spirit inside a Magic 8 Ball. Answer the question with exactly one word: "
        "YES if it is true or will happen, NO if it is false or will not happen, "
        "MAYBE if it cannot be known (the future, a private matter, taste, or not a yes/no question).\n\n"
        f"QUESTION:\n{question.strip()}\n\nANSWER:"
    )


WORDS = {"yes": "YES", "no": "NO", "maybe": "MAYBE"}
WORD_MEANING = {
    "yes": "if it is true, or will happen",
    "no": "if it is false, or will not happen",
    "maybe": "if it cannot be known (the future, a private matter, taste, or not a yes/no question)",
}
TEXT_WORD_MEANING = {
    "yes": "if the text says so",
    "no": "if the text says the opposite",
    "maybe": "if the text does not say",
}
# first tokens that count as each word (a tokenizer may split MAYBE into MAY + BE)
WORD_TOKENS = {"yes": {"yes", "ye", "y"}, "no": {"no", "n"}, "maybe": {"maybe", "may", "mayb", "m"}}


def build_word_prompt(question: str, order: list[str], text: str | None = None) -> str:
    """Ask for one word (YES / NO / MAYBE). The three words are listed in the given order, so rotating
    the order still cancels a habit of favouring the first one listed."""
    meaning = WORD_MEANING if text is None else TEXT_WORD_MEANING
    opts = "; ".join(f"{WORDS[k]} {meaning[k]}" for k in order)
    head = ("You are the spirit inside a Magic 8 Ball. Answer the question with exactly one word: " if text is None else
            "Read the text, then answer the question about it using only what the text says. Answer with exactly one word: ")
    body = f"TEXT:\n{text.strip()}\n\n" if text is not None else ""
    return f"{head}{opts}.\n\n{body}QUESTION:\n{question.strip()}\n\nANSWER:"


def parse_word_odds(data: dict, order: list[str]) -> list[float]:
    """First-token odds for YES / NO / MAYBE, lined up with `order`. Spellings (YES, Yes, yes) are pooled."""
    entries = data.get("logprobs")
    if not entries or not isinstance(entries, list):
        raise BackendError("Ollama reply had no logprobs. This needs Ollama v0.12.11 or newer.")
    tops = entries[0].get("top_logprobs") or [
        {"token": entries[0].get("token", ""), "logprob": entries[0].get("logprob", 0.0)}
    ]
    found: dict[str, list[float]] = {k: [] for k in KEYS}
    lowest = min(float(t["logprob"]) for t in tops)
    for t in tops:
        tok = str(t.get("token", "")).strip().lower().strip("*\"'`.")
        for k, names in WORD_TOKENS.items():
            if tok in names:
                found[k].append(float(t["logprob"]))
    if not any(found.values()):
        seen = ", ".join(repr(str(t.get("token", ""))) for t in tops[:5])
        raise BackendError(f"model did not start its reply with YES, NO or MAYBE (it preferred: {seen}).")
    floor = lowest - FLOOR_MARGIN
    return [_logsumexp(found[k]) if found[k] else floor for k in order]


def parse_plain(text: str) -> str:
    w = text.strip().lower().lstrip("*\"'` ").split()
    first = w[0].strip(".,!:*\"'`") if w else ""
    return first if first in KEYS else "maybe"


def _logsumexp(xs: list[float]) -> float:
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def parse_scores(data: dict, n: int = 3) -> list[float]:
    """Line up the model's first-token odds with the letters A, B, C. Spellings ("A", " A") are pooled;
    a letter the model did not rank gets a floor just below the lowest one it did rank."""
    entries = data.get("logprobs")
    if not entries or not isinstance(entries, list):
        raise BackendError("Ollama reply had no logprobs. This needs Ollama v0.12.11 or newer.")
    tops = entries[0].get("top_logprobs") or [
        {"token": entries[0].get("token", ""), "logprob": entries[0].get("logprob", 0.0)}
    ]
    wanted = {LETTERS[i].lower(): i for i in range(n)}
    found: list[list[float]] = [[] for _ in range(n)]
    lowest = min(float(t["logprob"]) for t in tops)
    for t in tops:
        key = str(t.get("token", "")).strip().lower()
        if key in wanted:
            found[wanted[key]].append(float(t["logprob"]))
    if not any(found):
        seen = ", ".join(repr(str(t.get("token", ""))) for t in tops[:5])
        raise BackendError(f"model did not pick A, B or C as its first token (it preferred: {seen}).")
    floor = lowest - FLOOR_MARGIN
    return [_logsumexp(f) if f else floor for f in found]


class OllamaBackend:
    def __init__(self, model: str = "gemma3", host: str = "http://127.0.0.1:11434", timeout: float = 60,
                 keep_alive: str = "30m", scoring: str = "letter"):
        if scoring not in ("letter", "word"):
            raise ValueError('scoring must be "letter" or "word"')
        self.scoring = scoring  # "letter": options shown as A, B, C and the letter's odds read; "word": the model's YES/NO/MAYBE odds
        self.keep_alive = keep_alive  # ask Ollama to keep the model in memory between questions
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}" + ("" if scoring == "letter" else ":word")

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.host + "/api/generate", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            e.close()
            try:
                detail = json.loads(body).get("error", body)
            except ValueError:
                detail = body
            if e.code == 404 or "not found" in str(detail).lower():
                raise BackendError(f"Ollama does not have model {self.model!r}. Pull it first: ollama pull {self.model}") from e
            raise BackendError(f"Ollama returned HTTP {e.code}: {detail}") from e
        except (socket.timeout, TimeoutError) as e:
            raise BackendError(f"Ollama at {self.host} did not answer within {self.timeout}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise BackendError(f"Ollama at {self.host} did not answer within {self.timeout}s") from e
            raise BackendError(f"cannot reach Ollama at {self.host} ({e.reason}). Is `ollama serve` running?") from e
        except ValueError as e:
            raise BackendError(f"Ollama sent a reply that is not JSON: {e}") from e

    def scores(self, question: str, order: list[str], text: str | None = None) -> list[float]:
        """Log-odds for the options, in the order they were shown (order is a permutation of yes/no/maybe).
        With `text`, the question is about that text and "maybe" means the text does not say."""
        if self.scoring == "word":
            prompt = build_word_prompt(question, order, text)
        else:
            prompt = build_prompt(question, order) if text is None else build_text_prompt(text, question, order)
        data = self._post({
            "model": self.model, "prompt": prompt, "stream": False, "keep_alive": self.keep_alive,
            "options": {"temperature": 0, "num_predict": 1},
            "logprobs": True, "top_logprobs": TOP_LOGPROBS,
        })
        return parse_word_odds(data, order) if self.scoring == "word" else parse_scores(data, len(order))

    def plain(self, question: str, text: str | None = None) -> str:
        """The usual way: let the model write one word. Used only as a yardstick in the benchmark."""
        prompt = build_plain_prompt(question) if text is None else build_plain_text_prompt(text, question)
        data = self._post({
            "model": self.model, "prompt": prompt, "stream": False, "keep_alive": self.keep_alive,
            "options": {"temperature": 0, "num_predict": 4},
        })
        return parse_plain(str(data.get("response", "")))

    def warm(self) -> None:
        """Load the model now, so the first real question is not the one that pays for it."""
        self._post({"model": self.model, "prompt": "", "stream": False, "keep_alive": self.keep_alive})
