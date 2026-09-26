# Scoreboard: gemma3

900 questions; calibration fitted on 294 dev items (temperature 4.25, commit threshold 0.774); every number below is from the other 606 test items.

| | Plain answer | One ordering | Shuffled | The ball (shuffled + calibrated) |
|---|---|---|---|---|
| Right group (yes / maybe / no) | 70.5% | 68.8% | 66.3% | 56.1% |
| Said a plain yes or no | 79.5% | 50.5% | 62.9% | 27.4% |
| Of those, wrong | 36.3% | 26.8% | 34.9% | 15.1% |
| Right on yes items (203) | 88.2% | 59.6% | 68.5% | 49.8% |
| Right on no items (203) | 63.1% | 50.7% | 53.7% | 19.7% |
| Right on maybe items (200) | 60.0% | 96.5% | 77.0% | 99.5% |
| Typical time | 347 ms | 386 ms | 1159 ms | 1159 ms |

"Plain answer" means asking the same model to write one word (YES, NO or MAYBE), the usual way.

## Gaps and whether they are outside noise

Paired bootstrap over test items, 95% interval for (ball minus other). Outside noise means the interval excludes 0.

- Right group, ball vs plain: -14.4 points [-19.3, -9.4] outside noise
- Right group, ball vs one order: -12.7 points [-15.5, -10.1] outside noise
- Right group, ball vs shuffled: -10.2 points [-14.2, -6.4] outside noise

## Does reordering the options change the answer?

Reading the model in a single fixed order, its pick changed when the options were reordered on 52.3% of items. The ball reads three orders and averages them, so its own answer does not depend on the order.

## Can you trust the confidence?

Confidence error = the average gap between how sure the model said it was and how often it was right (0 is perfect).

- Before calibration: 0.168
- After calibration: 0.059

## The strictness dial

The ball only says a plain yes or no when it is at least this sure. The setting is chosen on the dev items, then measured on the test items. A stricter ball says less and is wrong less often when it does speak.

| Wanted right when sure | Says yes or no on | Wrong when it says one | Right group overall |
|---|---|---|---|
| 75% | 53.6% | 30.2% | 67.2% |
| 80% | 45.9% | 25.5% | 65.2% |
| 85% | 36.8% | 21.5% | 61.4% |
| 90% (default) | 27.4% | 15.1% | 56.1% |
| 95% | 24.9% | 12.6% | 54.6% |

## By kind of question

| Kind | Should say | Items | Plain answer right | Ball right | Ball said hazy |
|---|---|---|---|---|---|
| animal | no or yes | 38 | 92.1% | 57.9% | 39.5% |
| arithmetic | no or yes | 38 | 57.9% | 7.9% | 86.8% |
| bigger | no or yes | 14 | 100.0% | 21.4% | 78.6% |
| calendar | no or yes | 38 | 60.5% | 7.9% | 73.7% |
| capital | no or yes | 38 | 97.4% | 94.7% | 5.3% |
| chemistry | no or yes | 38 | 86.8% | 34.2% | 60.5% |
| compare | no or yes | 40 | 60.0% | 10.0% | 87.5% |
| future | maybe | 50 | 84.0% | 100.0% | 100.0% |
| geo | no or yes | 38 | 68.4% | 36.8% | 57.9% |
| history | no or yes | 22 | 90.9% | 40.9% | 59.1% |
| number | no or yes | 32 | 75.0% | 15.6% | 84.4% |
| open | maybe | 50 | 34.0% | 100.0% | 100.0% |
| physical | no or yes | 32 | 68.8% | 53.1% | 31.2% |
| private | maybe | 50 | 50.0% | 100.0% | 100.0% |
| taste | maybe | 50 | 72.0% | 98.0% | 98.0% |
| word | no or yes | 38 | 71.1% | 31.6% | 57.9% |

## Does a stronger phrase mean a more reliable answer?

Each phrase the ball used on the test items, and how often the group it named was right.

| Phrase | Times said | Right |
|---|---|---|
| Yes definitely | 8 | 100.0% |
| It is decidedly so | 31 | 96.8% |
| You may rely on it | 29 | 86.2% |
| As I see it, yes | 23 | 82.6% |
| Most likely | 17 | 64.7% |
| Outlook good | 15 | 53.3% |
| Very doubtful | 17 | 100.0% |
| My sources say no | 10 | 100.0% |
| Don't count on it | 13 | 76.9% |
| Outlook not so good | 3 | 100.0% |
| (all hazy phrases together) | 440 | 45.2% |

