import importlib
import json
import os
import pathlib
import tempfile
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from eightball.answers import ANSWERS, all_answers, category_of
from eightball.calibrate import Calibration, fit, fit_temperature
from eightball.cli import main as cli_main
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


class Receipts(unittest.TestCase):
    """dev_samples reads calibration receipts. A valid file yields its dev items;
    a valid-JSON file that is not receipts is named, not tracebacked."""

    def _valid(self):
        from eightball.mock import MockBackend
        from eightball.engine import ORDERS
        b = MockBackend()
        items = []
        for i, (q, lab) in enumerate([("Is it a?", "yes"), ("Is it b?", "no"), ("Is it c?", "yes")]):
            items.append({"id": f"d{i}", "question": q, "label": lab, "split": "dev", "text": "t",
                          "raw": [b.scores(q, o, "t") for o in ORDERS]})
        return {"model": "mock", "scoring": "letter", "items": items}

    def test_valid_receipts_yield_dev_items_and_calibrate(self):
        from eightball.receipts import dev_samples
        d = tempfile.mkdtemp()
        path = os.path.join(d, "r.json")
        json.dump(self._valid(), open(path, "w"))
        samples, model = dev_samples(path)
        self.assertEqual(model, "mock")
        self.assertEqual(len(samples), 3)
        self.assertEqual(fit(samples, model).n_dev, 3)

    def test_a_non_receipts_json_file_is_named_not_raised(self):
        from eightball.receipts import dev_samples
        d = tempfile.mkdtemp()
        for bad in ({"not": "receipts"}, {"model": "m", "items": [{"split": "dev", "label": "yes"}]}):
            path = os.path.join(d, "bad.json")
            json.dump(bad, open(path, "w"))
            with self.assertRaises(ValueError):
                dev_samples(path)


class BenchRunArguments(unittest.TestCase):
    """bench/run.py --limit must be at least 1: 0 ran the whole set and a negative
    sliced from the end. The rejection is at parse time, before any file or model
    work, so this needs no model."""

    def test_non_positive_limit_is_refused(self):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
        run = importlib.import_module("run")
        saved = sys.argv
        try:
            for bad in ("0", "-3"):
                sys.argv = ["run.py", "--limit", bad, "--backend", "mock"]
                with self.assertRaises(SystemExit) as cm:
                    run.main()
                self.assertEqual(cm.exception.code, 2, bad)
        finally:
            sys.argv = saved


class BenchReceiptReaders(unittest.TestCase):
    """report.py and pick_scoring.py share receipts.dev_items and must, like it,
    end a malformed or missing file in one plain line, not a traceback."""

    def _run(self, script, arg):
        import subprocess
        root = pathlib.Path(__file__).resolve().parents[1]
        return subprocess.run([sys.executable, str(root / "bench" / script), arg],
                              capture_output=True, text=True)

    def test_bad_and_missing_files_end_in_one_plain_line(self):
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "bad.json")
        json.dump({"not": "receipts"}, open(bad, "w"))
        gone = os.path.join(d, "gone.json")
        for script, tag in (("report.py", "report:"), ("pick_scoring.py", "pick_scoring:")):
            for arg in (bad, gone):
                r = self._run(script, arg)
                self.assertNotEqual(r.returncode, 0, (script, arg))
                self.assertNotIn("Traceback", r.stderr, (script, arg))
                self.assertIn(tag, r.stderr, (script, arg))

    def test_report_on_a_dev_only_file_says_so(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        dev_only = next(root.glob("bench/receipts/*-dev.json"), None)
        if dev_only is None:
            self.skipTest("no dev-only receipts file committed")
        r = self._run("report.py", str(dev_only))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("no test items", r.stderr)


class CliFileErrors(unittest.TestCase):
    """A mistyped path is the commonest slip. Every command that reads a file
    ends in one plain "eightball: ..." line, not a FileNotFoundError traceback."""

    def _expect_clean_exit(self, argv):
        with self.assertRaises(SystemExit) as cm:
            cli_main(argv)
        self.assertIsInstance(cm.exception.code, str, argv)
        self.assertIn("eightball:", cm.exception.code)
        self.assertNotIn("Traceback", cm.exception.code)

    def test_missing_files_are_reported_not_raised(self):
        self._expect_clean_exit(["ask", "will it", "--backend", "mock", "--text-file", "/no/such/file.txt"])
        self._expect_clean_exit(["score", "/no/such/file.jsonl", "--backend", "mock"])
        self._expect_clean_exit(["calibrate", "--receipts", "/no/such/file.jsonl", "--out", "/tmp/eightball-test-out.json"])


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


class OrdersPerScoring(unittest.TestCase):
    def test_letters_rotate_all_three_words_read_one(self):
        from eightball.engine import orders_for, read_odds
        class W(MockBackend):
            scoring = "word"
        self.assertEqual(len(orders_for(MockBackend())), 3)
        self.assertEqual(orders_for(W()), [["yes", "no", "maybe"]])
        odds = read_odds(W(), "Is it so?")
        self.assertIsNone(odds.stability)
        r = Ball(W()).ask("Is it so?")
        self.assertIsNone(r["stability"])
        self.assertEqual(len(r["per_order"]), 1)

    def test_old_receipts_count_as_letter_readings(self):
        from eightball.receipts import scoring_of, used_orders
        self.assertEqual(scoring_of({}), "letter")
        self.assertEqual((used_orders("letter"), used_orders("word")), (3, 1))


class TextCalibration(unittest.TestCase):
    def test_text_questions_use_their_own_calibration(self):
        class Lean(MockBackend):
            def scores(self, q, order, text=None):
                return [1.0 if k == "yes" else 0.0 for k in order]
        strict, loose = Calibration(threshold=0.99), Calibration(threshold=0.1)
        b = Ball(Lean(), strict, loose)
        self.assertEqual(b.ask("Is this a good idea?")["category"], "maybe")               # general question: strict bar
        self.assertEqual(b.ask("Is it there?", text="It is there.")["category"], "yes")    # about a text: its own bar


class PickScoring(unittest.TestCase):
    def test_picks_the_higher_dev_accuracy(self):
        import subprocess, sys as _sys
        out = subprocess.run([_sys.executable, "bench/pick_scoring.py", "bench/receipts/gemma3-4b-text.json",
                              "bench/receipts/gemma3-4b-word-text.json"], capture_output=True, text=True, cwd=str(pathlib.Path(__file__).resolve().parents[1]))
        self.assertEqual(out.returncode, 0)
        self.assertIn("pick: word", out.stdout)


class Compare(unittest.TestCase):
    def test_compares_two_runs_on_shared_items(self):
        import subprocess, sys as _sys
        root = pathlib.Path(__file__).resolve().parents[1]
        out = subprocess.run([_sys.executable, "bench/compare.py", "bench/receipts/gemma3-4b.json", "bench/receipts/gemma3-4b-word.json"],
                             capture_output=True, text=True, cwd=str(root))
        self.assertEqual(out.returncode, 0)
        self.assertIn("shared test questions", out.stdout)
        self.assertIn("Right group,", out.stdout)


class MakeDemo(unittest.TestCase):
    def test_extra_receipts_file_adds_entries_with_their_own_label(self):
        import importlib, os, tempfile
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
        make_demo = importlib.import_module("make_demo")

        def fake_receipts(model, questions, seed_letter):
            from eightball.mock import MockBackend
            from eightball.engine import ORDERS
            b = MockBackend()
            items = []
            for i, (q, kind, label) in enumerate(questions):
                it = {"id": f"{seed_letter}{i}", "question": q, "label": label, "kind": kind,
                      "split": "dev" if i == 0 else "test", "text": "placeholder text"}
                it["raw"] = [b.scores(q, o, it["text"]) for o in ORDERS]
                it["ms_scores"] = 5
                items.append(it)
            return {"model": model, "scoring": "letter", "orders": ORDERS, "n": len(items), "items": items}

        main_qs = [("Is it stated?", "k1", "yes"), ("Is it not there?", "k1", "no"),
                   ("Is it stated?", "k1", "yes"), ("Is it not there?", "k1", "no")]
        extra_qs = [("Is the real fact there?", "k2", "yes"), ("Is the real fact not there?", "k2", "no"),
                    ("Is the real fact there?", "k2", "yes"), ("Is the real fact not there?", "k2", "no")]

        d = tempfile.mkdtemp()
        main_path = os.path.join(d, "main.json")
        extra_path = os.path.join(d, "extra.json")
        json.dump(fake_receipts("mock-main", main_qs, "m"), open(main_path, "w"))
        json.dump(fake_receipts("mock-extra", extra_qs, "e"), open(extra_path, "w"))

        main_entries, model, cal, scoring = make_demo.sampled_entries(main_path, per_kind=2, seed=1)
        extra_entries, _, _, _ = make_demo.sampled_entries(extra_path, per_kind=2, seed=1, label_suffix=", real document")
        self.assertTrue(all(", real document" in e["backend"] for e in extra_entries))
        self.assertTrue(all(", real document" not in e["backend"] for e in main_entries))
        self.assertGreater(len(extra_entries), 0)
