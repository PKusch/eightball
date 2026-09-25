.PHONY: test serve ask bench

PY ?= python3

test:
	PYTHONPATH=src $(PY) -m unittest discover -s tests

serve:
	PYTHONPATH=src $(PY) -m eightball serve --model gemma3

ask:
	PYTHONPATH=src $(PY) -m eightball ask --model gemma3 "Is Paris the capital of France?"

# a full run against a local Ollama model (about 20-40 minutes for 900 questions); writes bench/receipts/
bench:
	PYTHONPATH=src $(PY) bench/run.py --model gemma3
