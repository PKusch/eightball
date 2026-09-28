# Scoreboard: gemma3:12b

129 questions; calibration fitted on 45 dev items (temperature 8.5, commit threshold 0.706); every number below is from the other 84 test items.

| | Word match (no model) | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|---|
| Right group (yes / maybe / no) | 42.9% | 72.6% | 71.4% | 71.4% | 70.2% |
| Said a plain yes or no | 16.7% | 97.6% | 98.8% | 97.6% | 89.3% |
| Of those, wrong | 14.3% | 28.0% | 28.9% | 29.3% | 26.7% |
| Right on yes items (36) | 33.3% | 100.0% | 100.0% | 100.0% | 97.2% |
| Right on no items (24) | 0.0% | 95.8% | 95.8% | 91.7% | 83.3% |
| Right on maybe items (24) | 100.0% | 8.3% | 4.2% | 8.3% | 16.7% |
| Typical time | 0 ms | 860 ms | 868 ms | 2604 ms | 868 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs word match: +27.4 points [+9.5, +45.2] outside noise
- Right group, ball vs plain: -2.4 points [-8.3, +2.4] inside noise
- Right group, ball vs one order: -1.2 points [-7.1, +4.8] inside noise
- Right group, ball vs shuffled: -1.2 points [-6.0, +3.6] inside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 16.7% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.281
- After calibration: 0.187

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 97.6% | 28.0% | 72.6% |
| 80% | 89.3% | 26.7% | 70.2% |
| 85% | 89.3% | 26.7% | 70.2% |
| 90% (default) | 89.3% | 26.7% | 70.2% |
| 95% | 89.3% | 26.7% | 70.2% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| job_real | maybe or no or yes | 63 | 73.0% | 73.0% | 9.5% |
| lease_real | maybe or no or yes | 21 | 71.4% | 61.9% | 14.3% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| Most likely | 3 | 100.0% |
| Outlook good | 27 | 100.0% |
| Yes | 5 | 100.0% |
| Don't count on it | 33 | 42.4% |
| Outlook not so good | 7 | 85.7% |
| (all hazy phrases together) | 9 | 44.4% |

