import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import clean_body, compute_metrics, split_sentences  # noqa: E402

WORDS = " ".join(["word"] * 45)


class TextStatsTests(unittest.TestCase):
    def test_abbreviations_do_not_split(self):
        s = ("The gain was 0.91 (Fig. 3) as in Smith et al. and it held. "
             "A second sentence follows here.")
        self.assertEqual(len(split_sentences(s)), 2)

    def test_initials_and_ie_do_not_split(self):
        s = ("The model of A. F. Arif, i.e. the seven-parameter one, was used vs. the older one. "
             "It worked well here.")
        self.assertEqual(len(split_sentences(s)), 2)

    def test_hyphen_rejoin_and_reference_cut(self):
        text = (f"The effi-\nciency rose {WORDS}.\n\nReferences\n"
                f"[1] A. Author, Journal, 2010. {WORDS}")
        paras = clean_body(text)
        self.assertEqual(len(paras), 1)
        self.assertIn("efficiency", paras[0])
        self.assertNotIn("Author", paras[0])

    def test_caption_and_equation_lines_dropped(self):
        text = (f"Body text here {WORDS}.\nFig. 2 Variation of x with y\n"
                "η = (P_out / P_in) × 100 = 12.4 %")
        joined = " ".join(clean_body(text))
        self.assertNotIn("Variation", joined)
        self.assertNotIn("12.4", joined)

    def test_figure_sentence_is_kept(self):
        text = f"Fig. 1 shows the flow chart of the model {WORDS}."
        self.assertEqual(len(clean_body(text)), 1)

    def test_page_break_merge(self):
        text = (f"The panel {WORDS} cooling of the PV pan-\n"
                "M.U. Author / Journal 112 (2013) 300\n"
                "els is usually done to reduce stress.")
        paras = clean_body(text, line_paragraphs=True)
        self.assertEqual(len(paras), 1)
        self.assertIn("panels is usually done", paras[0])

    def test_uniform_vs_varied(self):
        uniform = [" ".join(["Alpha beta gamma delta epsilon zeta eta theta."] * 6)]
        varied = ["Short one here. This much longer sentence keeps going with many more words "
                  "than the first one did by far. Mid length sentence with eight words total."]
        self.assertEqual(compute_metrics(uniform)["sent_len_cv"], 0)
        self.assertGreater(compute_metrics(varied)["sent_len_cv"], 0.4)

    def test_connective_rate(self):
        p = ["However, it works well today. Moreover, it scales to large inputs. "
             "The rest is plain text here."]
        m = compute_metrics(p)
        self.assertGreater(m["conn_however_per_1000"], 0)
        self.assertGreater(m["connective_per_1000"], m["conn_however_per_1000"])

    def test_empty_input_does_not_crash(self):
        m = compute_metrics([])
        self.assertEqual(m["n_sentences"], 0)


if __name__ == "__main__":
    unittest.main()
