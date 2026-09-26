# Text-mode test set

**What it is.** 600 short texts, each with one yes/no question about it. The ball must answer:

- **yes**: the text says so.
- **no**: the text says the opposite.
- **maybe**: the text never says.

**The texts.** Eight kinds, 75 items each (25 yes, 25 no, 25 maybe): invoice, meeting invitation, flat
listing, product sheet, delivery notice, job posting, clinic reminder, class note. Each text is 3 to 7
sentences. All people, places and products are made up.

**How the right answer is guaranteed.** No model is asked. Every text is written from a small table of facts,
for example "deposit: 500 euros, pets: not allowed, floor: 3". Each question asks about ONE line of that table:

- **yes**: the question states what the table says.
- **no**: the question states a nearby wrong value ("450" for 500), or the opposite policy.
- **maybe**: the line was left out of the table, so the text never mentions it.

Yes, no and maybe use the same question shapes, so the wording gives nothing away.
Every stated fact is exact ("only", "sole", a plain number), so a wrong value is clearly wrong.
Nothing can be worked out by adding numbers or by hints from other sentences.

**How it is checked** (`python bench/check_text_questions.py`). For all 600 items:

1. The answer is worked out again from the fact table and the question alone.
2. The text is read back sentence by sentence against the known sentence patterns. The facts found in the
   words must equal the table, and the question is read back the same way.
   The answer worked out from those words must agree.
3. For "maybe", the text must contain none of the words that could touch the left-out topic.

It also checks ids, balance, both splits, and that the file is exactly what the generator makes.
The facts sit in each line under `facts` and the question under `ask`. A model must never be shown them.

**Splits.** About a third `dev` (192), the rest `test` (408), even for every kind and answer.

**Known limits.**

- The text is built from patterns, so it is plainer than real writing. Real documents can be vaguer.
- A program that only matches words can score well: if the question's topic and value appear in the text,
  say yes or no. If the topic is missing, say maybe. About 1 in 60 items adds a trap for this
  (a number that is in the text, but for a different topic).
- "Maybe" means "this text does not say". It does not mean the fact is unknowable in the world.
- Only eight kinds of document, English only, and no long texts.
- Wording is limited: 2 to 3 sentence patterns per topic, so a model can learn the patterns.
- Made-up names might by chance match a real person.
