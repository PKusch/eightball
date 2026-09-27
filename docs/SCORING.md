# Letter scoring or word scoring?

The ball reads a small model's odds instead of asking it to write an answer. There are two ways to read them.

**Letter scoring** (the old default): the options are shown as A, B, C and the model's odds for each letter are read. It reads the options in three different orders and averages them, which cancels out a model's habit of favouring whichever option it sees first.

**Word scoring** (`--scoring word`): the model is asked to answer with YES, NO or MAYBE, and the odds on that first word are read. It reads only the natural order, because on gemma3 4B, listing MAYBE anywhere but last made the model almost stop saying it.

On text mode (a question about a text you supply), letter scoring could barely say "no": right on only 71.6% of test questions and wrong 34.9% of the time it committed. Word scoring got 95.6% right and was wrong only 3.0% of the time it committed, and answered about three times faster. See [bench/receipts/gemma3-4b-text.md](../bench/receipts/gemma3-4b-text.md) and [bench/receipts/gemma3-4b-word-text.md](../bench/receipts/gemma3-4b-word-text.md).

## Which one should you use?

Run both benchmarks for your model, then:

```bash
python bench/pick_scoring.py bench/receipts/<model>.json bench/receipts/<model>-word.json
```

It compares them using only the questions set aside for fitting, never the ones used to measure the result, so the choice cannot be flattered by the test set. Whichever it picks, pass that as `--scoring` from then on (the command line, `serve`, and `bench/run.py` all take it), and calibrate again for that reading: `eightball calibrate --receipts bench/receipts/<model>-word.json --out calibration/<model>-word.json`.
