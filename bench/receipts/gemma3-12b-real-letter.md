# Scoreboard: gemma3:12b

129 questions; calibration fitted on 45 dev items (temperature 1.9, commit threshold 0.582); every number below is from the other 84 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (shuffled + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 42.9% | 72.6% | 98.8% | 98.8% | 96.4% |
| Said a plain yes or no | 16.7% | 97.6% | 71.4% | 71.4% | 67.9% |
| Of those, wrong | 14.3% | 28.0% | 1.7% | 1.7% | 0.0% |
| Right on yes items (36) | 33.3% | 100.0% | 100.0% | 100.0% | 100.0% |
| Right on no items (24) | 0.0% | 95.8% | 95.8% | 95.8% | 87.5% |
| Right on maybe items (24) | 100.0% | 8.3% | 100.0% | 100.0% | 100.0% |
| Typical time | 0 ms | 805 ms | 834 ms | 2502 ms | 2502 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +53.6 points [+42.9, +64.3] outside noise
- Right group, ball vs plain: +23.8 points [+14.3, +34.5] outside noise
- Right group, ball vs one order: -2.4 points [-6.0, +0.0] inside noise
- Right group, ball vs shuffled: -2.4 points [-6.0, +0.0] inside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 13.1% of items. The ball reads three orders and averages them, so its own answer does not depend on the order.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.041
- After calibration: 0.050

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 67.9% | 0.0% | 96.4% |
| 80% | 67.9% | 0.0% | 96.4% |
| 85% | 67.9% | 0.0% | 96.4% |
| 90% (default) | 67.9% | 0.0% | 96.4% |
| 95% | 58.3% | 0.0% | 86.9% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| job_real | maybe or no or yes | 63 | 73.0% | 96.8% | 30.2% |
| lease_real | maybe or no or yes | 21 | 71.4% | 95.2% | 38.1% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is certain | 35 | 100.0% |
| You may rely on it | 1 | 100.0% |
| My reply is no | 8 | 100.0% |
| Very doubtful | 4 | 100.0% |
| My sources say no | 1 | 100.0% |
| Outlook not so good | 8 | 100.0% |
| (all hazy phrases together) | 27 | 88.9% |

