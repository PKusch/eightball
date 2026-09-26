# Scoreboard: gemma3

600 questions; calibration fitted on 192 dev items (temperature 2.95, commit threshold 0.512); every number below is from the other 408 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 53.2% | 95.3% | 95.8% | 87.5% | 95.6% |
| Said a plain yes or no | 22.8% | 68.1% | 65.4% | 75.2% | 65.2% |
| Of those, wrong | 11.8% | 5.0% | 3.0% | 14.7% | 3.0% |
| Right on yes items (136) | 41.2% | 98.5% | 98.5% | 98.5% | 98.5% |
| Right on no items (136) | 19.1% | 95.6% | 91.9% | 94.1% | 91.2% |
| Right on maybe items (136) | 99.3% | 91.9% | 97.1% | 69.9% | 97.1% |
| Typical time | 0 ms | 166 ms | 124 ms | 370 ms | 124 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +42.4 points [+37.5, +47.1] outside noise
- Right group, ball vs plain: +0.2 points [-1.5, +2.0] inside noise
- Right group, ball vs one order: -0.2 points [-0.7, +0.0] inside noise
- Right group, ball vs shuffled: +8.1 points [+5.1, +11.0] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 32.4% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.031
- After calibration: 0.008

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 65.2% | 3.0% | 95.6% |
| 80% | 65.2% | 3.0% | 95.6% |
| 85% | 65.2% | 3.0% | 95.6% |
| 90% (default) | 65.2% | 3.0% | 95.6% |
| 95% | 65.2% | 3.0% | 95.6% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| class | maybe or no or yes | 51 | 94.1% | 92.2% | 39.2% |
| clinic | maybe or no or yes | 51 | 94.1% | 98.0% | 31.4% |
| delivery | maybe or no or yes | 51 | 98.0% | 96.1% | 37.3% |
| invoice | maybe or no or yes | 51 | 96.1% | 92.2% | 39.2% |
| job | maybe or no or yes | 51 | 94.1% | 98.0% | 33.3% |
| meeting | maybe or no or yes | 51 | 94.1% | 94.1% | 37.3% |
| product | maybe or no or yes | 51 | 94.1% | 96.1% | 29.4% |
| rental | maybe or no or yes | 51 | 98.0% | 98.0% | 31.4% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is certain | 133 | 100.0% |
| Without a doubt | 1 | 0.0% |
| It is decidedly so | 2 | 50.0% |
| As I see it, yes | 2 | 0.0% |
| My reply is no | 98 | 100.0% |
| Very doubtful | 9 | 100.0% |
| My sources say no | 6 | 83.3% |
| Don't count on it | 5 | 80.0% |
| Outlook not so good | 10 | 80.0% |
| (all hazy phrases together) | 142 | 93.0% |

