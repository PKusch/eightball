# Scoreboard: gemma3:12b

600 questions; calibration fitted on 192 dev items (temperature 9.0, commit threshold 0.715); every number below is from the other 408 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 53.2% | 74.8% | 76.2% | 79.4% | 81.6% |
| Said a plain yes or no | 22.8% | 90.9% | 89.5% | 86.8% | 78.7% |
| Of those, wrong | 11.8% | 27.2% | 26.0% | 23.4% | 19.3% |
| Right on yes items (136) | 41.2% | 99.3% | 99.3% | 100.0% | 97.8% |
| Right on no items (136) | 19.1% | 99.3% | 99.3% | 99.3% | 92.6% |
| Right on maybe items (136) | 99.3% | 25.7% | 30.1% | 39.0% | 54.4% |
| Typical time | 0 ms | 481 ms | 408 ms | 1226 ms | 408 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +28.4 points [+21.6, +35.0] outside noise
- Right group, ball vs plain: +6.9 points [+3.7, +10.3] outside noise
- Right group, ball vs one order: +5.4 points [+2.2, +8.6] outside noise
- Right group, ball vs shuffled: +2.2 points [-1.0, +5.1] inside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 21.8% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.223
- After calibration: 0.124

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 79.7% | 19.1% | 82.6% |
| 80% | 78.7% | 19.3% | 81.6% |
| 85% | 78.7% | 19.3% | 81.6% |
| 90% (default) | 78.7% | 19.3% | 81.6% |
| 95% | 78.7% | 19.3% | 81.6% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| class | maybe or no or yes | 51 | 68.6% | 80.4% | 25.5% |
| clinic | maybe or no or yes | 51 | 68.6% | 78.4% | 19.6% |
| delivery | maybe or no or yes | 51 | 76.5% | 80.4% | 17.6% |
| invoice | maybe or no or yes | 51 | 76.5% | 80.4% | 17.6% |
| job | maybe or no or yes | 51 | 70.6% | 80.4% | 13.7% |
| meeting | maybe or no or yes | 51 | 76.5% | 80.4% | 25.5% |
| product | maybe or no or yes | 51 | 78.4% | 82.4% | 19.6% |
| rental | maybe or no or yes | 51 | 82.4% | 90.2% | 31.4% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| Most likely | 2 | 100.0% |
| Outlook good | 108 | 100.0% |
| Yes | 23 | 100.0% |
| Don't count on it | 95 | 48.4% |
| Outlook not so good | 93 | 86.0% |
| (all hazy phrases together) | 87 | 85.1% |

