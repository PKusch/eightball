# Scoreboard: gemma3

129 questions; calibration fitted on 45 dev items (temperature 4.2, commit threshold 0.508); every number below is from the other 84 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (shuffled + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 42.9% | 82.1% | 85.7% | 85.7% | 79.8% |
| Said a plain yes or no | 16.7% | 83.3% | 67.9% | 66.7% | 58.3% |
| Of those, wrong | 14.3% | 21.4% | 15.8% | 14.3% | 12.2% |
| Right on yes items (36) | 33.3% | 100.0% | 97.2% | 97.2% | 94.4% |
| Right on no items (24) | 0.0% | 79.2% | 54.2% | 54.2% | 37.5% |
| Right on maybe items (24) | 100.0% | 58.3% | 100.0% | 100.0% | 100.0% |
| Typical time | 0 ms | 232 ms | 211 ms | 633 ms | 633 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +36.9 points [+26.2, +47.6] outside noise
- Right group, ball vs plain: -2.4 points [-13.1, +8.3] inside noise
- Right group, ball vs one order: -6.0 points [-11.9, -1.2] outside noise
- Right group, ball vs shuffled: -6.0 points [-10.7, -1.2] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 17.9% of items. The ball reads three orders and averages them, so its own answer does not depend on the order.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.114
- After calibration: 0.077

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 58.3% | 12.2% | 79.8% |
| 80% | 58.3% | 12.2% | 79.8% |
| 85% | 58.3% | 12.2% | 79.8% |
| 90% (default) | 58.3% | 12.2% | 79.8% |
| 95% | 42.9% | 0.0% | 71.4% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| job_real | maybe or no or yes | 63 | 77.8% | 77.8% | 39.7% |
| lease_real | maybe or no or yes | 21 | 95.2% | 85.7% | 47.6% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is decidedly so | 13 | 100.0% |
| You may rely on it | 17 | 100.0% |
| As I see it, yes | 3 | 100.0% |
| Outlook good | 3 | 33.3% |
| Yes | 1 | 0.0% |
| Signs point to yes | 3 | 0.0% |
| Very doubtful | 1 | 100.0% |
| My sources say no | 3 | 100.0% |
| Don't count on it | 1 | 100.0% |
| Outlook not so good | 4 | 100.0% |
| (all hazy phrases together) | 35 | 68.6% |

