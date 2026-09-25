# The test set: 900 questions with known right answers

`questions.jsonl` holds 900 questions, 300 for each right answer:

- **yes**: the statement is true.
- **no**: the statement is false.
- **maybe**: nobody can know, or there is no yes-or-no answer.

No language model was asked for an opinion. Every right answer follows from how the question was built. The same seed always makes the same file (`python bench/make_questions.py`), and `python bench/check_questions.py` re-checks it.

About a third of each group is marked `dev` (for tuning the ball) and the rest `test` (only for reporting). Every kind and answer appears in both.

## Yes and no questions (600)

Each kind has exactly as many yes as no. A no is made by changing one thing in a true statement (a wrong capital, a number that is close but wrong). The yes and no versions use the same sentence shapes, so the wording gives nothing away.

| Kind | Each | What it asks and why the answer is certain |
|---|---|---|
| capital | 28 | Is this city the capital of that country? A table of settled capitals. A no swaps in another real capital from the same part of the world. |
| arithmetic | 28 | Is 17 x 23 equal to 391? Sums, differences, products, exact divisions. A no is off by a small amount. The check redoes the sum. |
| bigger | 10 | Is 0.9 greater than 0.85? Number pairs, including digit swaps and decimals. |
| number | 24 | Prime, multiple of, perfect square, odd or even. A no for prime is a product of two primes (391 is 17 x 23). |
| physical | 24 | Fixed facts with a number: 60 seconds in a minute, water boils at 100 degrees. A no changes the number. |
| animal | 28 | Mammal, bird, fish and so on; can it fly; does it lay eggs. Tricky cases (a whale is not a fish) are on purpose. |
| geo | 28 | Which continent; which of two cities is further north (from a table of latitudes, at least 8 degrees apart); Northern or Southern Hemisphere; landlocked or not. |
| chemistry | 28 | Element symbols, which element has the lower atomic number (at least 5 apart), chemical formulas, solid, liquid or gas at room temperature. |
| calendar | 28 | Days in a month, weekday of a fixed date, leap years, which month comes first. Weekdays are worked out by the calendar, both for past and future dates. |
| word | 28 | Does a word contain, start with or end with a letter; is it longer than N letters; reads the same backwards; which letter comes first. |
| compare | 30 | Which is taller, heavier, longer, larger, faster, or has more people. Each pair differs by at least 1.4 times (some by 3 times or more), so there is no doubt. |
| history | 16 | Did a famous event happen in this year (a wrong year is 10 to 30 years off), or which of two events came first (at least 20 years apart). |

## Maybe questions (300)

Four kinds, 75 each, built from sentence templates filled with lists of subjects. No filler word or name is used more than 3 times.

| Kind | Example | Why it is maybe |
|---|---|---|
| future | Will Arsenal beat Chelsea in their next match? | A genuinely uncertain event: coin flips, dice, lottery numbers, evenly matched teams, weather months ahead, next week's share prices. Nothing practically certain is included. |
| private | Did I leave the oven on? | It is about the asker's own life. A stranger cannot know. |
| taste | Is jazz better than blues? | Opinion, taste, ethics or advice. There is no fact of the matter. |
| open | Why is the sky blue? | Not a yes-or-no question, or not a question at all: "Tell me a joke", a single word like "banana". |

Future, private and taste questions open with the same words as the yes/no ones (Is, Does, Will, Would, Did, Can).

## Known limits

- The right answer for maybe is a design choice. "Will Brazil win the next World Cup?" could be answered "very doubtful", but no one knows.
- Some questions in each group share a sentence template, so this is a test of many small skills, not of everyday talk.
- The `open` kind is easy to spot by shape (no yes/no form), and `Should` questions are all maybe. A ball that only reads the first word will score well on those.
- Small kinds (bigger 10 per answer, history 16) give wide error bars. Report per kind only with that in mind.
- Facts are ones that were settled in 2026. Future dates run to 2028, so old readings of "next" go stale; the calendar cut-off is fixed at 2026-09-25.
- Everything is in English, in British spelling, with plain ASCII place names (Brasilia, Bogota).
- Wrong answers are made by simple swaps. They are close but not the worst a person could invent.
