# Contract between the pieces

## The ball's answer (what the server and the page speak)

`POST /v1/ask` with `{"question": "Will I like this film?"}` returns:

```json
{
  "question": "Will I like this film?",
  "category": "yes",                 // "yes" | "maybe" | "no"
  "answer": "Signs point to yes",    // exactly one of the 20 phrases in src/eightball/answers.py
  "strength": 10,                    // 1 = strongest phrase in its group
  "confidence": 0.71,                // calibrated chance that the category is right (0..1)
  "probs": {"yes": 0.71, "no": 0.12, "maybe": 0.17},
  "stability": 1.0,                  // share of the option orderings that picked the same category
  "backend": "ollama:gemma3",
  "elapsed_ms": 640
}
```

- `GET /v1/answers` lists the 20 phrases: `[{"answer", "category", "strength"}]`.
- `GET /healthz` returns `{"ok": true, "backend": "..."}`.
- `GET /` serves `web/index.html`.
- Errors are `{"error": "..."}` with a 4xx/5xx status.

## Test set (bench/questions.jsonl), one JSON object per line

```json
{"id": "cap-0001", "question": "Is Paris the capital of France?", "label": "yes", "kind": "capital", "split": "dev"}
```

- `label` is what the ball *should* say: `yes` (true), `no` (false), `maybe` (cannot be known: the future, taste,
  private facts, or a question with no yes/no answer).
- Labels come from how each item was built (a table, arithmetic, a rule), never from a model's opinion.
- `split` is `dev` (used to fit calibration) or `test` (only used to report results).
