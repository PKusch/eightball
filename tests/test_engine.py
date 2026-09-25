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

    def test_no_cors_header_by_default(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz") as r:
            self.assertIsNone(r.headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()
