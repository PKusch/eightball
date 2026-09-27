.PHONY: test serve ask bench bench-text bench-word bench-word-text report score

PY ?= python3
MODEL ?= gemma3

test:
	PYTHONPATH=src $(PY) -m unittest discover -s tests

serve:
	PYTHONPATH=src $(PY) -m eightball serve --model $(MODEL)

ask:
	PYTHONPATH=src $(PY) -m eightball ask --model $(MODEL) "Is Paris the capital of France?"

# each of these takes roughly 10-25 minutes against a local Ollama model; writes bench/receipts/
bench:
	PYTHONPATH=src $(PY) bench/run.py --model $(MODEL) --out bench/receipts/$(MODEL).json

bench-word:
	PYTHONPATH=src $(PY) bench/run.py --model $(MODEL) --scoring word --out bench/receipts/$(MODEL)-word.json

bench-text:
	PYTHONPATH=src $(PY) bench/run.py --model $(MODEL) --scoring word --questions bench/text_questions.jsonl --out bench/receipts/$(MODEL)-word-text.json

# the scoreboard from an existing receipts file: make report FILE=bench/receipts/gemma3-4b.json
report:
	$(PY) bench/report.py $(FILE)

# grade the ball on your own questions: make score FILE=examples/my_questions.jsonl
score:
	PYTHONPATH=src $(PY) -m eightball score $(FILE) --model $(MODEL)
