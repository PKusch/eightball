# Blind audit of the test set

## Method

I drew 240 questions at random (seed 7), 80 for each label, and wrote them to a scratch file with the labels removed. I judged every question blind, using my own knowledge and Python for the sums, primes, leap years and weekdays. Only after all verdicts were fixed did I open the labelled file and compare.

## Agreement

Overall: 238 of 240 match, which is 99.2%.

| Label | Matches | Sampled | Rate |
|-------|---------|---------|------|
| yes   | 79 | 80 | 98.8% |
| no    | 79 | 80 | 98.8% |
| maybe | 80 | 80 | 100% |

## Every disagreement or dispute

| id | question | label | my verdict | reason |
|----|----------|-------|-----------|--------|
| ari-0024 | Does 928 plus 917 make 1945? | no | yes | My slip. The sum is 1845, not 1945, so the label "no" is correct. |
| cmp-0006 | Is Saturn farther from Earth than Jupiter? | yes | dispute | The gap changes as the planets orbit. Usually true, not always. |

## Notes

- No true labelling error found in this sample. The one disagreement was my own mistake.
- The one real dispute is cmp-0006. Saturn is farther on average, and at almost all times, so "yes" is a fair label.
- A few "maybe" items are open questions or commands (for example "Who invented the telephone?"). I also judged these as "maybe", so we agree, but they are not yes/no questions in the strict sense.
- This is a sample of 240 out of 900, so it cannot rule out a rare error in the other 660.
