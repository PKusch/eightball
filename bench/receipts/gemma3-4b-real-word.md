# Scoreboard: gemma3

129 questions; calibration fitted on 45 dev items (temperature 7.0, commit threshold 0.879); every number below is from the other 84 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 42.9% | 82.1% | 89.3% | 73.8% | 83.3% |
| Said a plain yes or no | 16.7% | 83.3% | 77.4% | 86.9% | 54.8% |
| Of those, wrong | 14.3% | 21.4% | 13.8% | 30.1% | 0.0% |
| Right on yes items (36) | 33.3% | 100.0% | 100.0% | 100.0% | 88.9% |
| Right on no items (24) | 0.0% | 79.2% | 83.3% | 62.5% | 58.3% |
| Right on maybe items (24) | 100.0% | 58.3% | 79.2% | 45.8% | 100.0% |
| Typical time | 0 ms | 234 ms | 207 ms | 622 ms | 207 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +40.5 points [+29.8, +51.2] outside noise
- Right group, ball vs plain: +1.2 points [-9.5, +11.9] inside noise
- Right group, ball vs one order: -6.0 points [-15.5, +3.6] inside noise
- Right group, ball vs shuffled: +9.5 points [-1.2, +20.2] inside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 26.2% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.101
- After calibration: 0.067

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 70.2% | 6.8% | 92.9% |
| 80% | 70.2% | 6.8% | 92.9% |
| 85% | 70.2% | 6.8% | 92.9% |
| 90% (default) | 54.8% | 0.0% | 83.3% |
| 95% | 39.3% | 0.0% | 67.9% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| job_real | maybe or no or yes | 63 | 77.8% | 85.7% | 41.3% |
| lease_real | maybe or no or yes | 21 | 95.2% | 76.2% | 57.1% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is decidedly so | 30 | 100.0% |
| You may rely on it | 1 | 100.0% |
| As I see it, yes | 1 | 100.0% |
| Very doubtful | 5 | 100.0% |
| My sources say no | 9 | 100.0% |
| (all hazy phrases together) | 38 | 63.2% |

