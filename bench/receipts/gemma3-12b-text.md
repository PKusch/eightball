# Scoreboard: gemma3:12b

600 questions; calibration fitted on 192 dev items (temperature 2.45, commit threshold 0.548); every number below is from the other 408 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (shuffled + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 53.2% | 74.8% | 97.3% | 96.1% | 95.1% |
| Said a plain yes or no | 22.8% | 90.9% | 64.0% | 62.7% | 61.8% |
| Of those, wrong | 11.8% | 27.2% | 0.0% | 0.0% | 0.0% |
| Right on yes items (136) | 41.2% | 99.3% | 100.0% | 100.0% | 100.0% |
| Right on no items (136) | 19.1% | 99.3% | 91.9% | 88.2% | 85.3% |
| Right on maybe items (136) | 99.3% | 25.7% | 100.0% | 100.0% | 100.0% |
| Typical time | 0 ms | 481 ms | 618 ms | 1854 ms | 1854 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +41.9 points [+37.3, +46.6] outside noise
- Right group, ball vs plain: +20.3 points [+15.7, +25.5] outside noise
- Right group, ball vs one order: -2.2 points [-3.7, -1.0] outside noise
- Right group, ball vs shuffled: -1.0 points [-2.0, -0.2] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 22.1% of items. The ball reads three orders and averages them, so its own answer does not depend on the order.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.078
- After calibration: 0.088

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 61.8% | 0.0% | 95.1% |
| 80% | 61.8% | 0.0% | 95.1% |
| 85% | 61.8% | 0.0% | 95.1% |
| 90% (default) | 61.8% | 0.0% | 95.1% |
| 95% | 61.8% | 0.0% | 95.1% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| class | maybe or no or yes | 51 | 68.6% | 94.1% | 39.2% |
| clinic | maybe or no or yes | 51 | 68.6% | 98.0% | 35.3% |
| delivery | maybe or no or yes | 51 | 76.5% | 92.2% | 41.2% |
| invoice | maybe or no or yes | 51 | 76.5% | 92.2% | 41.2% |
| job | maybe or no or yes | 51 | 70.6% | 98.0% | 35.3% |
| meeting | maybe or no or yes | 51 | 76.5% | 98.0% | 35.3% |
| product | maybe or no or yes | 51 | 78.4% | 94.1% | 39.2% |
| rental | maybe or no or yes | 51 | 82.4% | 94.1% | 39.2% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is certain | 32 | 100.0% |
| Without a doubt | 88 | 100.0% |
| Yes definitely | 10 | 100.0% |
| It is decidedly so | 3 | 100.0% |
| You may rely on it | 1 | 100.0% |
| As I see it, yes | 1 | 100.0% |
| Outlook good | 1 | 100.0% |
| My reply is no | 6 | 100.0% |
| Very doubtful | 20 | 100.0% |
| My sources say no | 5 | 100.0% |
| Don't count on it | 4 | 100.0% |
| Outlook not so good | 81 | 100.0% |
| (all hazy phrases together) | 156 | 87.2% |

