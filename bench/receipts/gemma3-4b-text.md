# Scoreboard: gemma3

600 questions; calibration fitted on 192 dev items (temperature 8.0, commit threshold 0.445); every number below is from the other 408 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (shuffled + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 53.2% | 95.3% | 75.0% | 72.3% | 71.3% |
| Said a plain yes or no | 22.8% | 68.1% | 43.1% | 39.7% | 38.2% |
| Of those, wrong | 11.8% | 5.0% | 2.8% | 1.9% | 0.6% |
| Right on yes items (136) | 41.2% | 98.5% | 97.1% | 98.5% | 97.1% |
| Right on no items (136) | 19.1% | 95.6% | 28.7% | 18.4% | 16.9% |
| Right on maybe items (136) | 99.3% | 91.9% | 99.3% | 100.0% | 100.0% |
| Typical time | 0 ms | 363 ms | 386 ms | 1156 ms | 1156 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +18.1 points [+13.2, +23.0] outside noise
- Right group, ball vs plain: -24.0 points [-28.9, -18.9] outside noise
- Right group, ball vs one order: -3.7 points [-5.9, -1.5] outside noise
- Right group, ball vs shuffled: -1.0 points [-2.0, -0.2] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 10.3% of items. The ball reads three orders and averages them, so its own answer does not depend on the order.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.243
- After calibration: 0.100

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 38.2% | 0.6% | 71.3% |
| 80% | 38.2% | 0.6% | 71.3% |
| 85% | 38.2% | 0.6% | 71.3% |
| 90% (default) | 38.2% | 0.6% | 71.3% |
| 95% | 38.2% | 0.6% | 71.3% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| class | maybe or no or yes | 51 | 94.1% | 68.6% | 64.7% |
| clinic | maybe or no or yes | 51 | 94.1% | 72.5% | 60.8% |
| delivery | maybe or no or yes | 51 | 98.0% | 68.6% | 64.7% |
| invoice | maybe or no or yes | 51 | 96.1% | 74.5% | 58.8% |
| job | maybe or no or yes | 51 | 94.1% | 72.5% | 58.8% |
| meeting | maybe or no or yes | 51 | 94.1% | 72.5% | 60.8% |
| product | maybe or no or yes | 51 | 94.1% | 68.6% | 64.7% |
| rental | maybe or no or yes | 51 | 98.0% | 72.5% | 60.8% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| Outlook good | 92 | 100.0% |
| Yes | 32 | 100.0% |
| Signs point to yes | 9 | 88.9% |
| Outlook not so good | 23 | 100.0% |
| (all hazy phrases together) | 252 | 54.0% |

