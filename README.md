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

## What has been checked, and what has not

- **Checked:** the 20 answers and their 10/5/5 split, that every answer is one of them, that shuffling cancels a first-place lean, that a weak yes turns hazy, and the server's error handling. 17 tests, run in CI on Python 3.11 to 3.13.
- **Checked:** the 900 test questions (300 yes, 300 no, 300 cannot-be-known). Every right answer comes from how the question was built, never from a model's opinion, and the script re-derives all 600 yes/no labels. A blind reader answered a random 240 of them and agreed on 238; the two exceptions were the reader's own arithmetic slip and one disputed comparison ([bench/AUDIT.md](bench/AUDIT.md)).
- **Not measured yet:** how often the ball is right. The benchmark (`bench/run.py`, then `bench/report.py`) is written and tested on a fake model, but has not been run on a real one, so this README quotes no accuracy. It will report the ball against simply asking the model for one word, with error bars.
- **Seen once, by hand:** gemma3 4B said "It is certain" to the capital of France, "Cannot predict now" to a lottery question, and "Concentrate and ask again" to "Tell me a joke". That is three examples, not a result.

## Known limits

- The first answer after starting can take about 15 seconds while the model loads.
- The 4B model is likely weak on arithmetic and calendar questions.
- Whether a phrase like "Signs point to yes" really is less reliable than "It is certain" is exactly what the benchmark is meant to show. It is not shown yet.
- Some yes/no kinds have few items (history 16, bigger 10), so their error bars will be wide.

## Next

Answering questions about a text you supply ("does this contract mention a fee?"), where "hazy" means the text does not say. Hazy phrases tied to a real reason. A bigger model side by side. A command to score the ball on your own questions.

## Layout

`src/eightball` the ball, server and command line · `web/index.html` the page · `bench/` questions, runner, scoreboard, audit · `docs/CONTRACT.md` the API shape.

MIT licensed.
