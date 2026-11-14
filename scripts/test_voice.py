import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract_voice import (classify_heading, render_markdown, sectioned_paragraphs,  # noqa: E402
                           voice_stats)

VOICE = os.path.join(HERE, "extract_voice.py")
FILL = " ".join(["The model was solved for the given conditions and the results were recorded."] * 6)


def paper(intro_extra="", results_extra=""):
    return {
        "introduction": [f"In the current work, a model was developed for the panel. {intro_extra} {FILL}"],
        "methods": [f"The thermal model was implemented in the solver. {FILL}"],
        "results": [f"Fig. 3 shows the variation of temperature. {results_extra} {FILL}"],
        "conclusions": [f"It was found that cooling reduces the temperature. {FILL}"],
        "other": [],
    }


class VoiceTests(unittest.TestCase):
    def test_classify_heading(self):
        self.assertEqual(classify_heading("1. Introduction"), "introduction")
        self.assertEqual(classify_heading("2. Mathematical model"), "methods")
        self.assertEqual(classify_heading("2 Materials and Methods"), "methods")
        self.assertEqual(classify_heading("3. Results and discussion"), "results")
        self.assertEqual(classify_heading("5. Conclusions"), "conclusions")
        self.assertIsNone(classify_heading("The model was solved for 3 cases."))
        self.assertIsNone(classify_heading("3.4686 A"))
        # Sub-headings do not switch the section: "3.2 Effect of design parameters" stays in results.
        self.assertIsNone(classify_heading("3.2 Effect of design parameters"))
        self.assertIsNone(classify_heading("2.1. Thermal model"))

    def test_person_and_passive(self):
        stats = voice_stats([paper(), paper(intro_extra="We also tested a second panel here.")])
        self.assertGreater(stats["person"]["overall"]["passive"], 0.5)
        self.assertGreater(stats["person"]["overall"]["we"], 0)
        self.assertLess(stats["person"]["overall"]["we"], 0.1)
        self.assertEqual(stats["person"]["methods"]["we"], 0)

    def test_tell_phrase_rate_and_paper_count(self):
        stats = voice_stats([paper(results_extra="It is important to note that the gain holds."),
                             paper(), paper()])
        tell = stats["tells"]["it is important to note"]
        self.assertEqual(tell["papers"], 1)
        self.assertGreater(tell["per_10k"], 0)
        self.assertEqual(stats["tells"]["delve"]["papers"], 0)

    def test_phrase_needs_enough_papers(self):
        papers = [paper(results_extra="The trend agrees with data reported in the literature."),
                  paper(results_extra="This matches values reported in the literature."),
                  paper(results_extra="A unique zebra phrase appears once.")]
        phrases = {p["phrase"] for p in voice_stats(papers)["phrases"]}
        self.assertIn("reported in the literature", phrases)
        self.assertFalse(any("zebra" in p for p in phrases))

    def test_openers_and_figure_style(self):
        stats = voice_stats([paper(), paper(), paper()])
        openers = {o["opener"] for o in stats["openers"]}
        self.assertIn("in the current", openers)
        self.assertEqual(stats["figures"]["fig_n_shows"], 3)

    def test_render_mentions_key_sections(self):
        md = render_markdown(voice_stats([paper(), paper(), paper()]))
        for heading in ("Person and voice", "Signature phrases", "Sentence openers",
                        "Phrases on the tell lists"):
            self.assertIn(heading, md)

    def test_sectioned_paragraphs_from_text_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p 2015.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Abstract text. {FILL}\n\n1. Introduction\n\nIntro para. {FILL}\n\n"
                        f"2. Numerical model\n\nMethod para. {FILL}\n\n"
                        f"3. Results and discussion\n\nResult para. {FILL}\n\n"
                        f"4. Conclusions\n\nConclusion para. {FILL}\n\nReferences\n\n[1] A. B, 2010.")
            sec = sectioned_paragraphs(path)
            self.assertTrue(sec["introduction"][0].startswith("Intro para"))
            self.assertTrue(sec["methods"][0].startswith("Method para"))
            self.assertTrue(sec["results"][0].startswith("Result para"))
            self.assertTrue(sec["conclusions"][0].startswith("Conclusion para"))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            body = (f"1. Introduction\n\nIn the current work a model was built. {FILL}\n\n"
                    f"2. Results\n\nFig. 2 shows the result. {FILL}\n\n{FILL}\n\n{FILL}")
            for name in ("A 2014.txt", "B 2016.txt", "C 2018.txt", "D 2025.txt"):
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    f.write(body)
            with open(os.path.join(d, "E 2017.txt"), "w", encoding="utf-8") as f:
                f.write("")
            out = os.path.join(d, "voice.md")
            r = subprocess.run([sys.executable, VOICE, d, "--out", out], capture_output=True,
                               text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("3 papers", md)
            self.assertNotIn("D 2025", md)
            self.assertIn("E 2017.txt", r.stderr)


if __name__ == "__main__":
    unittest.main()
