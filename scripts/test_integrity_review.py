"""Regression tests for the final-review findings on check_integrity.py."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_integrity import compare  # noqa: E402

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_integrity.py")


class MustFail(unittest.TestCase):
    """A changed technical detail must never produce a pass."""

    def bad(self, a, b):
        ok, report = compare(a, b)
        self.assertFalse(ok, f"wrongly passed:\n  {a}\n  {b}\n{report}")

    def test_exponents(self):
        self.bad("a Rayleigh number of 10^6 was used", "a Rayleigh number of 10^9 was used")
        self.bad("a grid of 2^10 cells", "a grid of 2^12 cells")
        self.bad("a current of 3.4 × 10⁻⁶ A", "a current of 3.4 × 10⁻⁷ A")
        self.bad("about 10⁶ cycles", "about 10⁹ cycles")

    def test_single_letter_and_greek_symbols(self):
        self.bad("where α is the absorptivity", "where β is the absorptivity")
        self.bad("where T is the wall value and h is fixed", "where P is the wall value and k is fixed")
        self.bad("so that h = Nu k / D holds", "so that h = Nu k / L holds")

    def test_operators_and_signs(self):
        self.bad("with p < 0.05 here", "with p > 0.05 here")
        self.bad("for Re ≤ 2300 only", "for Re ≥ 2300 only")
        self.bad("where q = a + b", "where q = a − b")
        self.bad("within ±0.5 K", "within 0.5 K")
        self.bad("cooled to − 40 °C", "cooled to 40 °C")
        self.bad("cooled to −40 °C", "cooled to 40 °C")

    def test_units_not_on_the_list(self):
        self.bad("a pulse of 5 ns", "a pulse of 5 ps")
        self.bad("at 30 psi", "at 30 ksi")
        self.bad("cured for 28 days", "cured for 28 weeks")
        self.bad("after 500 cycles", "after 500 hours")
        self.bad("tilted at 30°", "tilted at 30")
        self.bad("at 5 kPa", "at 5 MPa")

    def test_number_words_and_negation(self):
        self.bad("with three layers", "with four layers")
        self.bad("the stress did not exceed 250 MPa", "the stress did exceed 250 MPa")
        self.bad("less than 5 % of cases", "more than 5 % of cases")
        self.bad("above 300 K", "below 300 K")
        self.bad("measured before cooling", "measured after cooling")
        self.bad("tested without cooling", "tested with cooling")
        self.bad("a 5 % rise in output", "a 5 % drop in output")

    def test_element_symbols(self):
        self.bad("Cu nanoparticles were added", "Al nanoparticles were added")
        self.bad("a Si wafer was used", "a Ge wafer was used")

    def test_latex(self):
        self.bad("so $h = Nu k\n / D$ holds", "so $h = Nu k\n / L$ holds")
        self.bad(r"see \ref{fig:temp} here", r"see \ref{fig:eff} here")
        self.bad(r"by \eqref{eq:a} here", r"by \eqref{eq:b} here")

    def test_crossref_counts(self):
        self.bad("Fig. 3 shows A. Fig. 4 shows B. As in Fig. 3, C holds.",
                 "Fig. 3 shows A. Fig. 4 shows B. As in Fig. 4, C holds.")

    def test_author_year_citations(self):
        self.bad("as shown (Smith 2019) before", "as shown (Jones 2019) before")
        self.bad("as shown (see Smith, 2019) before", "as shown (see Jones, 2019) before")
        self.bad("Smith and Jones (2019) found it", "Smith and Brown (2019) found it")
        self.bad("Müller et al. (2019) found it", "Möller et al. (2019) found it")
        self.bad("Çengel (2019) found it", "Öztürk (2019) found it")

    def test_protect_phrase_across_line_break(self):
        ok, _ = compare("the thermal\nstress rose", "the heat load rose", protect=["thermal stress"])
        self.assertFalse(ok)


class MustPass(unittest.TestCase):
    """Legitimate edits must not be blocked."""

    def good(self, a, b):
        ok, report = compare(a, b)
        self.assertTrue(ok, f"wrongly failed:\n  {a}\n  {b}\n{report}")

    def test_em_dash_to_commas(self):
        self.good("The method—which uses 5 nodes—is fast.", "The method, which uses 5 nodes, is fast.")

    def test_spacing_variants(self):
        self.good("at 41.1 °C and 5 mm", "at 41.1°C and 5mm")
        self.good("with T=300 K", "with T = 300 K")
        self.good("about 12.4%", "about 12.4 percent")
        self.good("a size of 5 µm", "a size of 5 μm")

    def test_reference_list_forms(self):
        self.good("Figs. 3 and 4 show it", "Fig. 3 and Fig. 4 show it")
        self.good("as reported [3]–[5]", "as reported [3-5]")

    def test_scientific_notation_forms(self):
        self.good("a current of 3.4e-6 A", "a current of 3.4×10^-6 A")
        self.good("a current of 3.4 × 10−6 A", "a current of 3.4×10^{-6} A")

    def test_tense_and_same_direction_verbs(self):
        self.good("the output increases by 5 %", "the output increased by 5 %")

    def test_hyphenation_change_is_check_not_fail(self):
        ok, report = compare("the heat-transfer coefficient rose", "the heat transfer coefficient rose")
        self.assertTrue(ok, report)
        self.assertIn("CHECK", report)

    def test_mention_count_change_is_check_not_fail(self):
        ok, report = compare("The PV module ran hot. The PV module was cooled.",
                             "The PV module ran hot and was cooled.")
        self.assertTrue(ok, report)
        self.assertIn("CHECK", report)

    def test_number_order_change_is_flagged_for_confirmation(self):
        ok, report = compare("It fell from 58.3 °C to 32.5 °C.", "It fell from 32.5 °C to 58.3 °C.")
        self.assertIn("order", report)

    def test_accept_waives_a_named_polarity_word(self):
        a, b = "The method is not only fast but also cheap.", "The method is fast and cheap."
        ok, _ = compare(a, b)
        self.assertFalse(ok)
        ok, report = compare(a, b, accept=["not"])
        self.assertTrue(ok, report)
        self.assertIn("ACCEPTED", report)

    def test_strict_turns_checks_into_failures(self):
        ok, _ = compare("The PV module ran hot. The PV module was cooled.",
                        "The PV module ran hot and was cooled.", strict=True)
        self.assertFalse(ok)


class CliTests(unittest.TestCase):
    def run_cli(self, a_bytes, b_bytes, *extra):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.txt"), os.path.join(d, "b.txt")
            with open(a, "wb") as f:
                f.write(a_bytes)
            with open(b, "wb") as f:
                f.write(b_bytes)
            return subprocess.run([sys.executable, CHECK, a, b, *extra], capture_output=True,
                                  text=True, encoding="utf-8")

    def test_utf16_files_are_read_correctly(self):
        r = self.run_cli("It reached 58.3 °C at 250 MPa.".encode("utf-16"),
                         "It reached 53.8 °C at 520 MPa.".encode("utf-16"))
        self.assertEqual(r.returncode, 1, r.stdout)
        same = self.run_cli("It reached 58.3 °C at 250 MPa.".encode("utf-16"),
                            "It reached 58.3 °C at 250 MPa.".encode("utf-8"))
        self.assertEqual(same.returncode, 0, same.stdout)

    def test_empty_original_is_an_error_not_a_pass(self):
        r = self.run_cli(b"", b"")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
