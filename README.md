# eightball

[![tests](https://github.com/PKusch/eightball/actions/workflows/ci.yml/badge.svg)](https://github.com/PKusch/eightball/actions/workflows/ci.yml)

A Magic 8 Ball whose answers come from a small AI model running on your own computer.

Type a question. The ball answers with one of the 20 classic phrases, and only those: ten that mean yes, five that mean "not sure", five that mean no. It also tells you how sure it is, and it says "Reply hazy, try again" when it is not sure enough.

It is a toy for anything that is not a plain fact. The model knows nothing about your future or your private life.

## Try it

You need [Ollama](https://ollama.com) and a model (`ollama pull gemma3`). Nothing else to install.

```bash
python -m eightball ask "Is Paris the capital of France?"
```

```bash
python -m eightball serve --model gemma3   # then open http://127.0.0.1:8787
```

The page works without a model too: opened as a plain file it replays saved answers and says so on a badge.

## How it decides

1. The model reads the question and its odds for three options are read: yes, no, cannot be known. No text is written.
2. It does this three times with the options in a different order each time, and averages. Models lean towards whichever option they see first, and this cancels that out.
3. The odds are cooled down so "80% sure" is closer to right 80% of the time (fitted on labelled examples).
4. If the model is not sure enough, or it is not a yes/no question, the ball goes hazy.
5. Otherwise the phrase depends on how sure it is. "It is certain" is only said when the calibrated chance of being wrong is under 1 in 100.

## What we measured

Model: gemma3 4B on a laptop. 900 questions (300 yes, 300 no, 300 that cannot be known), built so the right answer is never a model's opinion (details in [bench/QUESTIONS.md](bench/QUESTIONS.md); a blind reader agreed with 238 of a 240-question sample, see [bench/AUDIT.md](bench/AUDIT.md)). The ball's settings were fitted on a third of the questions. Every number below is from the other 606. Full tables and every answer: [bench/receipts/gemma3-4b.md](bench/receipts/gemma3-4b.md).

| | Asking the model for one word | The ball |
|---|---|---|
| Says a plain yes or no on | 79.5% of questions | 27.4% of questions |
| When it says one, it is wrong | 36.3% of the time | 15.1% of the time |
| Right group overall (yes, hazy or no) | 70.5% | 56.1% |
| Typical time | 0.35 seconds | 1.2 seconds |

In plain words:

- **The ball is safer, not smarter.** It says yes or no far less often, and is wrong far less often when it does. Overall it scores lower than just asking, and that gap is real, not noise. The ball hands its unsure questions back as "hazy".
- **It goes hazy on the right things.** On questions nobody can answer (the future, private matters, taste, not-a-question) it went hazy 99.5% of the time. On questions the model cannot do, like arithmetic and calendar sums, it went hazy 74% to 88% of the time, where asking directly guesses.
- **Stronger phrases really are more reliable.** Of the ball's "yes" answers, "It is decidedly so" was right 97% of the time, "You may rely on it" 86%, "As I see it, yes" 83%, "Most likely" 65% and "Outlook good" 53%. The "no" phrases are also right in most cases, but each was said too few times to rank.
- **The order of the options matters a lot.** Reading the model in one fixed order, its pick changed when the options were reordered on 52% of questions. The ball averages three orders so its answer does not depend on that. That made it steadier, but it did not raise the overall score in this run.
- **Its confidence can be trusted more.** The gap between "how sure it says it is" and "how often it is right" fell from 0.168 to 0.059 (0 is perfect).
- **It falls a bit short of its own target.** The ball was set to be right 90% of the time when it speaks. On the unseen questions it was right about 85% of the time.

### How strict should it be?

One dial: how sure the ball must be before it says a plain yes or no. Chosen on the fitting questions, measured on the unseen ones.

| Wanted right when it speaks | Speaks on | Wrong when it speaks |
|---|---|---|
| 75% | 53.6% of questions | 30.2% |
| 80% | 45.9% | 25.5% |
| 85% | 36.8% | 21.5% |
| 90% (the default) | 27.4% | 15.1% |

## Try it on your own questions

Put questions and the right answers in a file, one per line, and see how often the ball is wrongly sure:

```bash
python -m eightball score examples/my_questions.jsonl --model gemma3
```

Each line looks like `{"question": "Is Paris the capital of France?", "label": "yes"}`, where the label is `yes`, `no` or `maybe`.

## Tests

30 automated tests (`make test`) run on every push, on Python 3.11 to 3.13. They check the 20 answers and their 10/5/5 split, that shuffling cancels a first-place lean, that a weak yes turns hazy, the server's error handling, text mode, and the scoring command.

## Known limits

- One small model, one laptop, one run. Timing was measured while other jobs shared the machine.
- Some kinds have few questions (history 22, bigger 14 in the test half), so their numbers are rough.
- The questions are built from templates, so they are cleaner than real life. A model can also learn a template.
- "Cannot be known" is a design choice: "Will Brazil win the World Cup?" is labelled that way, though someone could call it "very doubtful".
- Health, safety, money and feelings questions always go hazy with "please ask a person", whatever the model thinks.

## Next

Text mode is built (`--text`, or `"text"` in the API) but its results are not in yet. A bigger model side by side is next.

## Layout

`src/eightball` the ball, server and command line · `web/index.html` the page · `bench/` questions, runner, scoreboard, audit · `docs/CONTRACT.md` the API shape.

MIT licensed.
