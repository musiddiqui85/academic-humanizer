import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_integrity import compare, extract_technical  # noqa: E402

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_integrity.py")

ORIGINAL = (
    "The PV/T collector was cooled at 0.05 m/s, which reduced the cell temperature from 41.1 °C "
    "to 32.5 °C (Table 3) and raised the efficiency by 12.4 % [3, 7]. A Nd:YAG laser and SiC "
    "particles were used, and the heat-transfer coefficient followed Eq. (4) with $h = Nu k / D$ "
    "as reported by Sarhaddi et al. (2010). The seven-parameter model gave 3.4686 × 10^-6 A."
)


class IntegrityTests(unittest.TestCase):
    def test_identical_passes(self):
        ok, report = compare(ORIGINAL, ORIGINAL)
        self.assertTrue(ok, report)

    def test_extracts_each_category(self):
        t = extract_technical(ORIGINAL)
        self.assertIn("12.4%", t["numbers"])
        self.assertIn("3", t["citations"])
        self.assertIn("7", t["citations"])
        self.assertIn("sarhaddi 2010", t["citations"])
        self.assertIn("table 3", t["crossrefs"])
        self.assertIn("eq 4", t["crossrefs"])
        self.assertIn("PV/T", t["symbols"])
        self.assertIn("Nd:YAG", t["symbols"])
        self.assertIn("SiC", t["symbols"])
        self.assertIn("heat-transfer", t["terms"])
        self.assertEqual(len(t["math"]), 1)
        self.assertIn("0.05 m/s", t["quantities"])
        self.assertIn("41.1 °C", t["quantities"])
        # Citation numbers and cross-reference numbers are not double-counted as numbers.
        self.assertNotIn("7", t["numbers"])
        self.assertNotIn("2010", t["numbers"])

    def test_changed_number_fails(self):
        ok, report = compare(ORIGINAL, ORIGINAL.replace("12.4 %", "12.5 %"))
        self.assertFalse(ok)
        self.assertIn("12.4%", report)

    def test_dropped_citation_fails(self):
        ok, report = compare(ORIGINAL, ORIGINAL.replace("[3, 7]", "[3]"))
        self.assertFalse(ok)
        self.assertIn("citations", report)

    def test_dropped_term_fails(self):
        for term, repl in [("PV/T", "hybrid"), ("Nd:YAG", "solid-state"), ("SiC", "carbide"),
                           ("heat-transfer coefficient", "convection coefficient")]:
            ok, _ = compare(ORIGINAL, ORIGINAL.replace(term, repl))
            self.assertFalse(ok, term)

    def test_changed_math_fails(self):
        ok, _ = compare(ORIGINAL, ORIGINAL.replace("$h = Nu k / D$", "$h = Nu k / L$"))
        self.assertFalse(ok)

    def test_changed_unit_fails(self):
        ok, report = compare(ORIGINAL, ORIGINAL.replace("0.05 m/s", "0.05 m/min"))
        self.assertFalse(ok)
        self.assertIn("quantities", report)

    def test_reworded_prose_passes(self):
        rewrite = (
            "Cooling the PV/T collector at 0.05 m/s reduced the cell temperature from 41.1 °C to "
            "32.5 °C (Table 3). The efficiency rose by 12.4% [3,7]. We used a Nd:YAG laser and "
            "SiC particles. The heat-transfer coefficient followed Eq. 4, with $h = Nu k / D$, as "
            "reported by Sarhaddi et al. (2010). The seven-parameter model gave 3.4686 × 10^-6 A."
        )
        ok, report = compare(ORIGINAL, rewrite)
        self.assertTrue(ok, report)

    def test_range_dash_styles_match(self):
        ok, report = compare("a gain of 4--7 points [2-4]", "a gain of 4–7 points [2, 3, 4]")
        self.assertTrue(ok, report)

    def test_added_number_fails(self):
        ok, report = compare("The gain was large.", "The gain was 15% larger.")
        self.assertFalse(ok)
        self.assertIn("added", report)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.txt"), os.path.join(d, "b.txt")
            for path, text in [(a, ORIGINAL), (b, ORIGINAL.replace("41.1", "41.7"))]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            same = subprocess.run([sys.executable, CHECK, a, a], capture_output=True, text=True,
                                  encoding="utf-8")
            diff = subprocess.run([sys.executable, CHECK, a, b], capture_output=True, text=True,
                                  encoding="utf-8")
            self.assertEqual(same.returncode, 0, same.stdout)
            self.assertIn("PASS", same.stdout)
            self.assertEqual(diff.returncode, 1)
            self.assertIn("FAIL", diff.stdout)


if __name__ == "__main__":
    unittest.main()
