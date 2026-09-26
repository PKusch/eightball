import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from eightball.answers import ANSWERS, all_answers, category_of
from eightball.calibrate import Calibration, fit, fit_temperature
from eightball.engine import Ball, ORDERS, is_yes_no_question, strength_of
from eightball.mock import MockBackend
from eightball.server import make_handler


class Answers(unittest.TestCase):
    def test_classic_twenty(self):
        self.assertEqual([len(ANSWERS[c]) for c in ("yes", "maybe", "no")], [10, 5, 5])
        self.assertEqual(len({a["answer"] for a in all_answers()}), 20)
        self.assertEqual(category_of("Very doubtful"), "no")


class Engine(unittest.TestCase):
    def test_every_answer_is_one_of_the_twenty(self):
        b = Ball(MockBackend())
        allowed = {a["answer"] for a in all_answers()}
        for q in ["Is Paris the capital of France?", "Will it rain tomorrow?", "Tell me a joke", "Is it not so?", "x"]:
            self.assertIn(b.ask(q)["answer"], allowed)

    def test_orders_put_every_option_in_every_place(self):
        for pos in range(3):
            self.assertEqual({o[pos] for o in ORDERS}, {"yes", "no", "maybe"})

    def test_shuffling_cancels_a_first_place_lean(self):
        class Biased(MockBackend):  # always loves the first listed option, knows nothing
            def scores(self, q, order):
                return [3.0, 0.0, 0.0]
        r = Ball(Biased()).ask("Is this a good idea?")
        self.assertAlmostEqual(r["probs"]["yes"], r["probs"]["no"], places=6)
        self.assertLess(r["stability"], 1.0)

    def test_unsure_model_gets_a_hazy_phrase(self):
        class Unsure(MockBackend):
            def scores(self, q, order):
                return [0.0, 0.0, 0.0]
        r = Ball(Unsure(), Calibration(threshold=0.6)).ask("Is this a good idea?")
        self.assertEqual((r["category"], r["committed"]), ("maybe", False))

    def test_not_a_question_is_concentrate(self):
        self.assertEqual(Ball(MockBackend()).ask("Tell me a joke")["answer"], "Concentrate and ask again")
        self.assertFalse(is_yes_no_question("What is the capital of France?"))
        self.assertTrue(is_yes_no_question("Is Paris the capital of France?"))

    def test_future_question_cannot_predict(self):
        self.assertEqual(Ball(MockBackend()).ask("Will it rain tomorrow?")["answer"], "Cannot predict now")

    def test_more_sure_means_stronger_phrase(self):
        s = [strength_of("yes", c) for c in (0.999, 0.97, 0.9, 0.75, 0.6)]
        self.assertEqual(s, sorted(s))
        self.assertEqual(strength_of("yes", 0.999), 1)
        self.assertEqual(strength_of("yes", 0.6), 10)
        self.assertEqual(strength_of("no", 0.999), 1)
        self.assertEqual(strength_of("no", 0.6), 5)

    def test_threshold_turns_a_weak_yes_hazy(self):
        class Lean(MockBackend):
            def scores(self, q, order):
                return [1.0 if k == "yes" else 0.0 for k in order]
        weak = Ball(Lean(), Calibration(threshold=0.9)).ask("Is this a good idea?")
        self.assertEqual(weak["category"], "maybe")
        self.assertEqual(weak["leaning"], "yes")
        self.assertEqual(Ball(Lean(), Calibration(threshold=0.2)).ask("Is this a good idea?")["category"], "yes")

    def test_empty_question_is_refused(self):
        with self.assertRaises(ValueError):
            Ball(MockBackend()).ask("   ")


class Calib(unittest.TestCase):
    def test_overconfident_model_is_cooled(self):
        # always 95% sure of yes, but right only 60% of the time
        p = {"yes": 0.95, "no": 0.03, "maybe": 0.02}
        samples = [(p, "yes")] * 6 + [(p, "no")] * 4
        self.assertGreater(fit_temperature(samples), 1.0)

    def test_fit_threshold_reaches_target(self):
        good = {"yes": 0.9, "no": 0.05, "maybe": 0.05}
        bad = {"yes": 0.5, "no": 0.4, "maybe": 0.1}
        samples = [(good, "yes")] * 20 + [(bad, "yes")] * 5 + [(bad, "no")] * 5
        cal = fit(samples, "m", target=0.9)
        self.assertGreater(cal.threshold, cal.apply(bad)["yes"])

    def test_save_and_load(self):
        import tempfile, os
        p = os.path.join(tempfile.mkdtemp(), "c.json")
        Calibration(1.4, 0.7, "m", 10, 0.9).save(p)
        self.assertEqual(Calibration.load(p).threshold, 0.7)


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Ball(MockBackend()), cors=False))
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, body: bytes):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/ask", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_ask(self):
        code, body = self.post(json.dumps({"question": "Is Paris the capital of France?"}).encode())
        self.assertEqual(code, 200)
        self.assertIn(body["answer"], {a["answer"] for a in all_answers()})
        for k in ("category", "strength", "confidence", "probs", "stability", "backend", "elapsed_ms"):
            self.assertIn(k, body)

    def test_bad_bodies(self):
        self.assertEqual(self.post(b"not json")[0], 400)
        self.assertEqual(self.post(b'{"question": 7}')[0], 400)
        self.assertEqual(self.post(b'{"question": "  "}')[0], 400)
        self.assertEqual(self.post(json.dumps({"question": "x" * 600}).encode())[0], 400)

    def test_answers_and_health(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/v1/answers") as r:
            self.assertEqual(len(json.loads(r.read())), 20)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz") as r:
            self.assertTrue(json.loads(r.read())["ok"])

    def test_text_mode_over_http(self):
        code, body = self.post(json.dumps({"question": "Is the deposit 500 euros?", "text": "Rent is 900. Deposit: unknown."}).encode())
        self.assertEqual((code, body["reason"]), (200, "not_stated"))
        self.assertEqual(self.post(json.dumps({"question": "Is it?", "text": 5}).encode())[0], 400)

    def test_no_cors_header_by_default(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz") as r:
            self.assertIsNone(r.headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()


class Warm(unittest.TestCase):
    def test_keep_alive_is_sent_and_warm_loads(self):
        from eightball.backend import OllamaBackend
        sent = []

        class Spy(OllamaBackend):
            def _post(self, payload):
                sent.append(payload)
                return {"logprobs": [{"top_logprobs": [{"token": "A", "logprob": -0.1}]}], "response": "yes"}

        b = Spy("m")
        b.scores("Is it?", ["yes", "no", "maybe"])
        b.plain("Is it?")
        b.warm()
        self.assertTrue(all(p["keep_alive"] == "30m" for p in sent))
        self.assertEqual(len(sent), 3)


class Reasons(unittest.TestCase):
    def test_sensitive_is_always_hazy_and_says_ask_a_person(self):
        r = Ball(MockBackend()).ask("Should I stop taking my medication?")
        self.assertEqual((r["category"], r["committed"], r["reason"]), ("maybe", False, "sensitive"))
        self.assertIn("ask a person", r["explanation"].lower())

    def test_every_hazy_answer_has_a_reason_and_committed_has_none(self):
        b = Ball(MockBackend())
        self.assertIsNone(b.ask("Is Paris the capital of France?")["reason"])
        self.assertEqual(b.ask("Will it rain tomorrow?")["reason"], "future")
        self.assertEqual(b.ask("Tell me a joke")["reason"], "not_a_question")

    def test_per_order_shows_each_shuffle(self):
        r = Ball(MockBackend()).ask("Is Paris the capital of France?")
        self.assertEqual(len(r["per_order"]), 3)
        self.assertEqual([o["order"] for o in r["per_order"]], ORDERS)
        self.assertTrue(all(o["pick"] in ("yes", "no", "maybe") for o in r["per_order"]))

    def test_benchmark_questions_are_not_hit_by_the_guard_wrongly(self):
        from eightball.engine import SENSITIVE
        import pathlib
        for l in pathlib.Path(__file__).resolve().parents[1].joinpath("bench", "questions.jsonl").read_text().splitlines():
            it = json.loads(l)
            if SENSITIVE.search(it["question"]):
                self.assertEqual(it["label"], "maybe", it["question"])


class Score(unittest.TestCase):
    def test_scores_your_own_questions(self):
        import os, tempfile
        from eightball.score import load_items, score
        path = os.path.join(tempfile.mkdtemp(), "q.jsonl")
        with open(path, "w") as f:
            f.write('{"question": "Is Paris the capital of France?", "label": "yes"}\n')
            f.write('{"question": "Will it rain tomorrow?", "label": "maybe"}\n')
            f.write('{"question": "Is the moon made of cheese?", "label": "no"}\n')  # the mock says yes: a wrong-sure miss
        res = score(Ball(MockBackend()), load_items(path))
        self.assertEqual(res["n"], 3)
        self.assertAlmostEqual(res["right"], 2 / 3)
        self.assertAlmostEqual(res["wrong_when_sure"], 1 / 2)
        self.assertEqual(res["misses"][0]["should_say"], "no")

    def test_bad_file_is_explained(self):
        import os, tempfile
        from eightball.score import load_items
        path = os.path.join(tempfile.mkdtemp(), "q.jsonl")
        open(path, "w").write('{"question": "Is it?", "label": "sure"}\n')
        with self.assertRaises(ValueError):
            load_items(path)


class TextMode(unittest.TestCase):
    def test_not_stated_is_hazy_with_its_own_reason(self):
        r = Ball(MockBackend()).ask("Is the deposit 500 euros?", text="Rent is 900 euros. Deposit: unknown.")
        self.assertEqual((r["category"], r["reason"], r["text_mode"]), ("maybe", "not_stated", True))
        self.assertEqual(r["explanation"], "The text does not say.")

    def test_text_says_so(self):
        r = Ball(MockBackend()).ask("Is the deposit 500 euros?", text="Rent is 900 euros. Deposit is 500 euros.")
        self.assertEqual(r["category"], "yes")

    def test_health_guard_does_not_apply_to_a_supplied_text(self):
        r = Ball(MockBackend()).ask("Is the appointment about a medication review?", text="Your medication review is on Monday.")
        self.assertNotEqual(r["reason"], "sensitive")

    def test_blank_text_means_general_question(self):
        self.assertNotIn("text_mode", Ball(MockBackend()).ask("Is Paris the capital of France?", text="   "))

    def test_prompt_shows_the_text(self):
        from eightball.backend import build_text_prompt
        p = build_text_prompt("Rent is 900.", "Is rent 900?", ["yes", "no", "maybe"])
        self.assertIn("TEXT:\nRent is 900.", p)
        self.assertIn("Not stated", p)


class WordScoring(unittest.TestCase):
    def test_word_prompt_lists_the_words_in_the_given_order(self):
        from eightball.backend import build_word_prompt
        p = build_word_prompt("Is it?", ["no", "maybe", "yes"])
        self.assertLess(p.index("NO "), p.index("MAYBE "))
        self.assertLess(p.index("MAYBE "), p.index("YES "))

    def test_word_odds_line_up_with_the_order_and_pool_spellings(self):
        from eightball.backend import parse_word_odds
        data = {"logprobs": [{"top_logprobs": [
            {"token": "YES", "logprob": -0.5}, {"token": "Yes", "logprob": -2.0},
            {"token": "NO", "logprob": -1.5}, {"token": "MAY", "logprob": -4.0}]}]}
        s = parse_word_odds(data, ["no", "maybe", "yes"])
        self.assertGreater(s[2], s[0])          # yes (two spellings pooled) beats no
        self.assertGreater(s[0], s[1])          # no beats maybe
        self.assertGreater(s[2], -0.5)          # pooling raises it above the single best spelling

    def test_word_backend_reads_words_not_letters(self):
        from eightball.backend import OllamaBackend
        class Spy(OllamaBackend):
            def _post(self, payload):
                self.prompt = payload["prompt"]
                return {"logprobs": [{"top_logprobs": [{"token": "NO", "logprob": -0.1}]}]}
        b = Spy("m", scoring="word")
        s = b.scores("Is it?", ["yes", "no", "maybe"])
        self.assertEqual(s.index(max(s)), 1)
        self.assertIn("exactly one word", b.prompt)
        with self.assertRaises(ValueError):
            OllamaBackend("m", scoring="nope")
