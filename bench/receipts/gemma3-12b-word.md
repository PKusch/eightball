# Scoreboard: gemma3:12b

900 questions; calibration fitted on 294 dev items (temperature 5.0, commit threshold 0.881); every number below is from the other 606 test items.

| | Plain answer | One ordering | Three orders averaged | The ball (natural order + calibrated) |
|---|---|---|---|---|
| Right group (yes / maybe / no) | 88.3% | 88.3% | 87.5% | 79.7% |
| Said a plain yes or no | 67.5% | 67.7% | 69.1% | 51.7% |
| Of those, wrong | 16.9% | 16.8% | 18.1% | 9.3% |
| Right on yes items (203) | 89.7% | 89.7% | 91.6% | 74.9% |
| Right on no items (203) | 77.8% | 78.3% | 77.3% | 65.0% |
| Right on maybe items (200) | 97.5% | 97.0% | 93.5% | 99.5% |
| Typical time | 434 ms | 364 ms | 1093 ms | 364 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs plain: -8.6 points [-11.1, -6.3] outside noise
- Right group, ball vs one order: -8.6 points [-11.1, -6.3] outside noise
- Right group, ball vs shuffled: -7.8 points [-10.4, -5.1] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 7.6% of items. In word mode the ball reads only the natural order (yes, no, maybe): on the fitting questions, other orders made the model almost stop saying maybe, so averaging them in hurt.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.113
- After calibration: 0.035

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 67.3% | 16.4% | 88.6% |
| 80% | 67.3% | 16.4% | 88.6% |
| 85% | 64.4% | 13.8% | 88.0% |
| 90% (default) | 51.7% | 9.3% | 79.7% |
| 95% | 35.8% | 2.3% | 68.0% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| animal | no or yes | 38 | 97.4% | 97.4% | 2.6% |
| arithmetic | no or yes | 38 | 52.6% | 18.4% | 78.9% |
| bigger | no or yes | 14 | 92.9% | 92.9% | 0.0% |
| calendar | no or yes | 38 | 76.3% | 31.6% | 63.2% |
| capital | no or yes | 38 | 100.0% | 100.0% | 0.0% |
| chemistry | no or yes | 38 | 94.7% | 89.5% | 7.9% |
| compare | no or yes | 40 | 77.5% | 65.0% | 25.0% |
| future | maybe | 50 | 100.0% | 100.0% | 100.0% |
| geo | no or yes | 38 | 94.7% | 84.2% | 13.2% |
| history | no or yes | 22 | 100.0% | 90.9% | 9.1% |
| number | no or yes | 32 | 65.6% | 56.2% | 18.8% |
| open | maybe | 50 | 96.0% | 100.0% | 100.0% |
| physical | no or yes | 32 | 84.4% | 78.1% | 9.4% |
| private | maybe | 50 | 98.0% | 100.0% | 100.0% |
| taste | maybe | 50 | 96.0% | 98.0% | 98.0% |
| word | no or yes | 38 | 78.9% | 57.9% | 26.3% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| It is decidedly so | 34 | 97.1% |
| You may rely on it | 94 | 94.7% |
| As I see it, yes | 43 | 69.8% |
| Very doubtful | 73 | 100.0% |
| My sources say no | 69 | 85.5% |
| (all hazy phrases together) | 293 | 67.9% |

