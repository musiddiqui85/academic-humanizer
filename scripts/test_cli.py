import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build_profile.py")
ANALYZE = os.path.join(HERE, "analyze_draft.py")


def varied_text(n_sentences=200, seed=1):
    rng = random.Random(seed)
    vocab = ("panel module cooling stress thermal model energy system result value method "
             "increase reduce shows under with from the of and a in for is was").split()
    paras, sents = [], []
    for i in range(n_sentences):
        n = rng.choice([5, 8, 12, 18, 25, 33, 41])
        words = [rng.choice(vocab) for _ in range(n)]
        sents.append("The " + " ".join(words) + ".")
        if len(sents) == rng.choice([4, 6, 9]) or i == n_sentences - 1:
            paras.append(" ".join(sents))
            sents = []
    if sents:
        paras.append(" ".join(sents))
    return "\n\n".join(paras)


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                          encoding="utf-8")


class BuildProfileTests(unittest.TestCase):
    def test_build_skips_empty_and_filters_year(self):
        with tempfile.TemporaryDirectory() as d:
            for name, body in [("A 2015.txt", varied_text()), ("B 2024.txt", varied_text(seed=2)),
                               ("C 2016.txt", ""), ("A 2015_compressed.txt", varied_text())]:
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    f.write(body)
            out = os.path.join(d, "profile.json")
            r = run(BUILD, d, "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8") as f:
                prof = json.load(f)
            self.assertEqual([p["file"] for p in prof["papers"]], ["A 2015.txt"])
            self.assertIn("C 2016.txt", [s["file"] for s in prof["skipped"]])
            self.assertIn("C 2016.txt", r.stderr)
            self.assertEqual(prof["max_year"], 2022)
            self.assertIn("sent_len_cv", prof["metrics"])
            self.assertEqual(set(prof["metrics"]["sent_len_cv"]), {"mean", "sd", "min", "max"})


def write_profile(d, **overrides):
    metrics = {"sent_len_cv": {"mean": 0.5, "sd": 0.05, "min": 0.4, "max": 0.6},
               "connective_per_1000": {"mean": 5.0, "sd": 1.0, "min": 3.0, "max": 7.0},
               "conn_moreover_per_1000": {"mean": 0.5, "sd": 0.2, "min": 0.0, "max": 1.0},
               "mattr": {"mean": 0.6, "sd": 0.0, "min": 0.6, "max": 0.6}}
    metrics.update(overrides)
    path = os.path.join(d, "profile.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"built": "2026-11-14", "max_year": 2022, "papers": [], "skipped": [],
                   "metrics": metrics}, f)
    return path


class AnalyzeDraftTests(unittest.TestCase):
    def test_uniform_draft_flags_low_variation(self):
        with tempfile.TemporaryDirectory() as d:
            prof = write_profile(d)
            draft = os.path.join(d, "draft.txt")
            with open(draft, "w", encoding="utf-8") as f:
                f.write(" ".join(["Moreover, the module shows a stable and uniform response."] * 20))
            r = run(ANALYZE, draft, "--profile", prof, "--raw")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertRegex(r.stdout, r"sent_len_cv.*LOW")
            self.assertIn("too even", r.stdout)
            self.assertIn("moreover", r.stdout.lower())
            # A metric whose author SD is 0 is never flagged.
            self.assertNotRegex(r.stdout, r"mattr.*(LOW|HIGH)")

    def test_short_draft_notice(self):
        with tempfile.TemporaryDirectory() as d:
            prof = write_profile(d)
            draft = os.path.join(d, "draft.txt")
            with open(draft, "w", encoding="utf-8") as f:
                f.write("One short sentence here. Another short sentence here. A third one here.")
            r = run(ANALYZE, draft, "--profile", prof, "--raw")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Too short to judge", r.stdout)
            self.assertNotIn("LOW", r.stdout)

    def test_share_not_flagged_low_when_author_floor_is_under_one_sentence(self):
        with tempfile.TemporaryDirectory() as d:
            prof = write_profile(d, initial_connective_share={"mean": 0.05, "sd": 0.03,
                                                              "min": 0.0, "max": 0.1})
            draft = os.path.join(d, "draft.txt")
            with open(draft, "w", encoding="utf-8") as f:
                f.write(" ".join(["The module shows a stable and uniform response."] * 16))
            r = run(ANALYZE, draft, "--profile", prof, "--raw", "--json")
            self.assertNotIn("initial_connective_share", json.loads(r.stdout)["flags"])

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as d:
            prof = write_profile(d)
            draft = os.path.join(d, "draft.txt")
            with open(draft, "w", encoding="utf-8") as f:
                f.write(" ".join(["Moreover, the module shows a stable and uniform response."] * 20))
            r = run(ANALYZE, draft, "--profile", prof, "--raw", "--json")
            data = json.loads(r.stdout)
            self.assertEqual(data["flags"]["sent_len_cv"], "LOW")

    def test_missing_profile_message(self):
        with tempfile.TemporaryDirectory() as d:
            draft = os.path.join(d, "draft.txt")
            with open(draft, "w", encoding="utf-8") as f:
                f.write("Text.")
            r = run(ANALYZE, draft, "--profile", os.path.join(d, "nope.json"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("build_profile.py", r.stderr)


if __name__ == "__main__":
    unittest.main()
