# Changelog

## Unreleased
- A bad or missing file now ends in one plain line, never a traceback: `ask --text-file`, `score`, `calibrate --receipts`, and the `bench/` scripts (`run`, `report`, `pick_scoring`, `compare`). The four benchmark scripts share one validated receipts reader, and `report` on a dev-only receipts file says so instead of crashing.
- A real-document test set (129 hand-written questions over 32 real U.S. federal job postings and excerpts from 4 real SEC-filed leases, not templated). Each model picked the same reading it picked on made-up documents, confirmed fresh. 4B's accuracy genuinely drops on real text (95.6% to 83.3%, confidence intervals don't overlap); 12B barely moves (95.1% to 96.4%). Both never wrong when they committed, on a small sample.
- Text mode measured: reading letters could barely say "no" in text mode (right group 71.6%, wrong 34.9% of the time it spoke, against 87.5% right just asking). Reading the model's own YES/NO/MAYBE word odds fixed it: 95.6% right, wrong only 3.0% of the time it spoke, and three times faster.
- Word scoring (`--scoring word`): the model answers with a word instead of a letter and that word's odds are read. It reads only the natural order (yes, no, maybe); on the fitting questions, other orders made the model almost stop saying "maybe".
- Text-mode questions get their own calibration file, separate from plain questions.
- First real reading, gemma3 4B on the 900 general questions: right on 56.1% overall, but wrong only 15.1% of the time when it commits to yes or no (asking the model directly: wrong 36.3% of the time).
- Hazy answers now say why (torn between yes and no, leaning but unsure, about the future, cannot be known, or not a yes/no question). Health, safety, money and feelings questions always go hazy with "please ask a person".
- `eightball score`: grade the ball on your own questions.
- Text mode: give the ball a short text and it answers only from that text; "cannot be known" becomes "the text does not say".
- The model is kept loaded and warmed at startup: a warm answer takes about 0.2 seconds instead of 5 to 16.
- 900-question and 600-text-question test sets, both built so the right answer comes from how the question was made, not a model's opinion. Blind audit of the first set: 238 of 240 agreed.
- Page: the glossy ball, live mode, an honest replay mode with no invented answers, a "show the odds" panel, a shake test, and the reason a hazy answer was hazy.

## 0.1.0 (2026-09-25)
- The ball: reads the model's odds in three shuffled orders, cools them down, and answers with one of the 20 classic Magic 8 Ball phrases.
- Local server (`/v1/ask`) and command line.
