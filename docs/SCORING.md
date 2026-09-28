# Letter scoring or word scoring?

The ball reads a small model's odds instead of asking it to write an answer. There are two ways to read them.

**Letter scoring** (the default): the options are shown as A, B, C and the model's odds for each letter are read. It reads the options in three different orders and averages them, which cancels out a model's habit of favouring whichever option it sees first.

**Word scoring** (`--scoring word`): the model is asked to answer with YES, NO or MAYBE, and the odds on that first word are read. It reads only the natural order, because on both models tried, listing MAYBE anywhere but last made the model almost stop saying it.

## There is no single right answer

We measured both readings, on two models, on two kinds of question (general knowledge, and questions about a supplied text). All four combinations disagree with each other:

| | General questions | Text mode |
|---|---|---|
| gemma3 4B | letter wins (71.8% vs 69.4% on the fitting questions) | word wins by a lot (95.6% right, wrong 3.0% of the time it speaks, vs letter's 71.6% right, wrong 34.9%) |
| gemma3 12B | word wins (88.8% vs 80.6% on the fitting questions) | letter wins by a lot (95.1% right, wrong 0.0% of the time it speaks, vs word's 81.6% right, wrong 19.3%) |

In other words: 4B and 12B want the *opposite* reading for the same task. There is no rule like "always use word scoring for text" that holds across models. Full tables: [bench/receipts/gemma3-4b.md](../bench/receipts/gemma3-4b.md), [bench/receipts/gemma3-4b-word.md](../bench/receipts/gemma3-4b-word.md), [bench/receipts/gemma3-4b-text.md](../bench/receipts/gemma3-4b-text.md), [bench/receipts/gemma3-4b-word-text.md](../bench/receipts/gemma3-4b-word-text.md), [bench/receipts/gemma3-12b-word.md](../bench/receipts/gemma3-12b-word.md), [bench/receipts/gemma3-12b-text.md](../bench/receipts/gemma3-12b-text.md), [bench/receipts/gemma3-12b-word-text.md](../bench/receipts/gemma3-12b-word-text.md).

## Confirmed on real documents

Both models' choices above were made on made-up documents. When checked fresh on a small set of real ones (32 real job postings, 4 real leases - [bench/REAL_QUESTIONS.md](../bench/REAL_QUESTIONS.md)), each model picked the exact same reading again on that set's own fitting questions: 4B still wants word, 12B still wants letter. The pick travels; the accuracy doesn't always - see the README's "Does this hold up on real documents?" section.

## Which one should you use?

Run both benchmarks for your model, then:

```bash
python bench/pick_scoring.py bench/receipts/<model>.json bench/receipts/<model>-word.json
```

It compares them using only the questions set aside for fitting, never the ones used to measure the result, so the choice cannot be flattered by the test set. That is enough to pick correctly: on both models here, the fitting-only pick matched what the full test set later confirmed. Whichever it picks, pass that as `--scoring` from then on (the command line, `serve`, and `bench/run.py` all take it), and calibrate again for that reading: `eightball calibrate --receipts bench/receipts/<model>-word.json --out calibration/<model>-word.json`.
