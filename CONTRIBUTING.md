# Contributing

The most useful thing you can send is a question the ball gets wrong: one where it
commits to a plain yes or no and the honest answer is the other way, or one where it
goes hazy when a person would not. Open an issue with the question, what the ball
said, and the model and scoring you ran (`--model`, `--scoring`).

## How the question sets are made

Nothing in `bench/questions.jsonl` is edited by hand. It is built from templates and
fact tables in `bench/make_questions.py`, and `bench/check_questions.py` rebuilds it,
recomputes every yes/no label from the question text, and fails CI if the committed
file differs or a label disagrees. So a new kind of question goes in `make_questions.py`
with the rule that decides its answer, not into the `.jsonl` directly. The real-document
set (`bench/real/`) is the exception: those questions are hand-written against real text,
checked by `bench/check_real_text_questions.py`.

## Running it

```bash
make test            # or: PYTHONPATH=src python -m unittest discover -s tests
make check           # the question-set validators CI runs
```

No model is needed for the tests — they use a stand-in backend. For a real reading you
need [Ollama](https://ollama.com) and a pulled model; see the README.

## In plain words

Write anything a person reads — answers, messages, docs — so it says what a thing does
and why, not how. One idea per sentence. Put the plain meaning next to any number.
