# Scoreboard: gemma3

900 questions; calibration fitted on 294 dev items (temperature 11.0, commit threshold 0.820); every number below is from the other 606 test items.

| | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|
| Right group (yes / maybe / no) | 70.5% | 71.6% | 73.9% | 61.6% |
| Said a plain yes or no | 79.5% | 78.4% | 74.4% | 33.0% |
| Of those, wrong | 36.3% | 35.4% | 33.5% | 13.5% |
| Right on yes items (203) | 88.2% | 87.2% | 85.2% | 55.7% |
| Right on no items (203) | 63.1% | 64.0% | 62.6% | 29.6% |
| Right on maybe items (200) | 60.0% | 63.5% | 74.0% | 100.0% |
| Typical time | 154 ms | 111 ms | 334 ms | 111 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs plain: -8.9 points [-13.5, -4.3] outside noise
- Right group, ball vs one order: -10.1 points [-14.7, -5.6] outside noise
- Right group, ball vs shuffled: -12.4 points [-16.5, -8.1] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 16.0% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.268
- After calibration: 0.021

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 50.7% | 19.2% | 72.9% |
| 80% | 42.1% | 16.9% | 67.7% |
| 85% | 38.4% | 14.2% | 66.0% |
| 90% (default) | 33.0% | 13.5% | 61.6% |
| 95% | 17.3% | 4.8% | 49.5% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| animal | no or yes | 38 | 92.1% | 68.4% | 28.9% |
| arithmetic | no or yes | 38 | 57.9% | 13.2% | 76.3% |
| bigger | no or yes | 14 | 100.0% | 57.1% | 42.9% |
| calendar | no or yes | 38 | 60.5% | 15.8% | 76.3% |
| capital | no or yes | 38 | 97.4% | 94.7% | 5.3% |
| chemistry | no or yes | 38 | 86.8% | 47.4% | 47.4% |
| compare | no or yes | 40 | 60.0% | 17.5% | 80.0% |
| future | maybe | 50 | 84.0% | 100.0% | 100.0% |
| geo | no or yes | 38 | 68.4% | 42.1% | 47.4% |
| history | no or yes | 22 | 90.9% | 59.1% | 40.9% |
| number | no or yes | 32 | 75.0% | 25.0% | 68.8% |
| open | maybe | 50 | 34.0% | 100.0% | 100.0% |
| physical | no or yes | 32 | 68.8% | 43.8% | 43.8% |
| private | maybe | 50 | 50.0% | 100.0% | 100.0% |
| taste | maybe | 50 | 72.0% | 100.0% | 100.0% |
| word | no or yes | 38 | 71.1% | 42.1% | 42.1% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| Most likely | 128 | 84.4% |
| Outlook good | 9 | 55.6% |
| Don't count on it | 63 | 95.2% |
| (all hazy phrases together) | 406 | 49.3% |

