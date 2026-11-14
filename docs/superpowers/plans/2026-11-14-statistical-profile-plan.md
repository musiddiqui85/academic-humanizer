# Statistical Profile Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the academic-humanizer skill measure a draft's statistical shape against the author's own pre-2023 papers and rewrite only where the gap is large.

**Architecture:** One shared metrics module, two thin command-line scripts (build the profile, analyze a draft), one JSON profile file, and a new Layer 7 in `SKILL.md` that tells the model when and how to run them.

**Tech Stack:** Python 3 standard library, `pdftotext` (already installed), `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-14-statistical-profile-design.md`

All paths below are relative to the repository root.

## Global Constraints

- Python standard library and `pdftotext` only. No package installs.
- Baseline = PDFs in `<folder of the author's papers>` whose filename year is <= 2022, skipping names ending `_compressed.pdf`. Expected count: 22.
- Held-out test text = the 2023, 2024, 2026 papers.
- Never change a number, equation, citation, or claim to move a statistic.
- No detector-score targeting, no perplexity scoring.
- Commit after each task on branch `feat/statistical-profile`. `author_profile.json` is git-ignored (personal data); never push without the author asking.

## Review Focus

1. Abbreviations and decimals ("et al.", "Fig. 3", "i.e.", "0.91") must not split a sentence. Test in Task 1.
2. Two-column PDF text with hyphenated line breaks ("effi-\nciency") must rejoin into one word. Test in Task 1.
3. The reference list, captions, and equation lines must not enter the statistics. Test in Task 1.
4. A very short draft (under 8 sentences) must produce a "too short to judge" notice, not flags or a crash. Test in Task 3.
5. A PDF that yields no text (scanned) must be skipped with a warning naming the file, and the build must continue. Test in Task 2.

---

### Task 1: Shared metrics module

**Files:**
- Create: `scripts/textstats.py`
- Test: `scripts/test_textstats.py`

**Interfaces (produces):**
- `extract_text(path: str) -> str`: `.pdf` via `pdftotext -layout`-free default mode; `.docx` via `zipfile` + `word/document.xml`; `.tex` with commands, math, and environments `equation|align|table|figure` stripped; `.txt`/`.md` read as UTF-8.
- `clean_body(text: str) -> list[str]`: returns paragraphs of body prose. Rejoins hyphenated line breaks; cuts everything from a line matching `^(references|bibliography|acknowledg)` (case-insensitive) onward; drops lines starting `Fig`, `Figure`, `Table`; drops lines where under 60% of characters are letters or spaces; drops paragraphs under 40 words.
- `split_sentences(paragraph: str) -> list[str]`: split on `.?!` followed by space and a capital or `(`, protecting `et al.`, `e.g.`, `i.e.`, `Fig.`, `Figs.`, `Eq.`, `Eqs.`, `Ref.`, `Refs.`, `vs.`, `cf.`, `approx.`, `No.`, single capital initials, and decimals. Drop sentences under 3 words.
- `compute_metrics(paragraphs: list[str]) -> dict[str, float]` with exactly these keys:
  `n_sentences`, `n_words`, `sent_len_mean`, `sent_len_sd`, `sent_len_cv`, `short_share` (<= 10 words), `long_share` (>= 35 words), `adjacent_diff_mean` (mean absolute word-count difference between neighbouring sentences in a paragraph), `para_len_cv` (sentences per paragraph), `opener_repeat_rate` (share of sentences whose first word equals the previous sentence's first word), `connective_per_1000`, `comma_per_1000`, `semicolon_per_1000`, `colon_per_1000`, `paren_per_1000`, `mattr` (moving-average type-token ratio, window 100 words), plus one key `conn_<word>_per_1000` for each connective in `CONNECTIVES`.
- `CONNECTIVES = ["however", "moreover", "furthermore", "additionally", "therefore", "thus", "hence", "consequently", "notably", "importantly", "overall", "specifically", "in addition", "in particular", "in contrast", "on the other hand"]`

- [ ] **Step 1: Write failing tests** in `scripts/test_textstats.py`:

```python
def test_abbreviations_do_not_split():
    s = "The gain was 0.91 (Fig. 3) as in Smith et al. and it held. A second sentence follows here."
    assert len(split_sentences(s)) == 2

def test_hyphen_rejoin_and_reference_cut():
    words = " ".join(["word"] * 45)
    text = f"The effi-\nciency rose {words}.\n\nReferences\n[1] A. Author, Journal, 2010. {words}"
    paras = clean_body(text)
    assert len(paras) == 1 and "efficiency" in paras[0] and "Author" not in paras[0]

def test_caption_and_equation_lines_dropped():
    words = " ".join(["word"] * 45)
    text = f"Body text here {words}.\nFig. 2 Variation of x with y\nη = (P_out / P_in) × 100 = 12.4 %"
    assert "Variation" not in " ".join(clean_body(text))

def test_uniform_vs_varied():
    uniform = [" ".join(["Alpha beta gamma delta epsilon zeta eta theta."] * 6)]
    varied = ["Short one here. " + "This much longer sentence keeps going with many more words than the first one did by far. " + "Mid length sentence with eight words total."]
    assert compute_metrics(uniform)["sent_len_cv"] == 0
    assert compute_metrics(varied)["sent_len_cv"] > 0.4

def test_connective_rate():
    p = ["However, it works well today. Moreover, it scales to large inputs. The rest is plain text here."]
    m = compute_metrics(p)
    assert m["conn_however_per_1000"] > 0 and m["connective_per_1000"] > m["conn_however_per_1000"]
```

- [ ] **Step 2: Run** `python -m unittest scripts/test_textstats.py` from the skill folder. Expected: import error.
- [ ] **Step 3: Implement** `scripts/textstats.py` to the Interfaces above.
- [ ] **Step 4: Run** the tests again. Expected: 5 pass.

### Task 2: Profile builder

**Files:**
- Create: `scripts/build_profile.py`
- Create (output): `author_profile.json`
- Test: `scripts/test_cli.py`

**Interfaces:**
- Consumes: `extract_text`, `clean_body`, `compute_metrics`.
- Produces: CLI `python scripts/build_profile.py <folder> [--max-year 2022] [--out author_profile.json]`. Year = last 4-digit number in the filename. Output JSON: `{"built": "<date>", "max_year": 2022, "papers": [{"file", "year", "n_sentences"}], "skipped": [{"file", "reason"}], "metrics": {"<key>": {"mean", "sd", "min", "max"}}}` where statistics run across papers. Papers with fewer than 50 sentences after cleaning are skipped with reason `"too little text"`.

- [ ] **Step 1: Write failing test** `test_build_skips_empty_and_filters_year`: in a temp folder create `A 2015.txt` (200 varied sentences), `B 2024.txt` (same), `C 2016.txt` (empty), `A 2015_compressed.txt`; run the CLI; assert `papers` lists only `A 2015.txt`, `skipped` contains `C 2016.txt`, exit code 0. (The builder accepts any extension `extract_text` supports.)
- [ ] **Step 2: Run** `python -m unittest scripts/test_cli.py`. Expected: fail.
- [ ] **Step 3: Implement** `scripts/build_profile.py`.
- [ ] **Step 4: Run** the test. Expected: pass.
- [ ] **Step 5: Build the real profile:** `python scripts/build_profile.py "<folder of the author's papers>" --out author_profile.json`. Expected: 22 papers used or a named reason for each one skipped. Open two extracted papers' cleaned text and confirm by eye that references, captions, and equations are gone; fix cleaning rules if not.

### Task 3: Draft analyzer

**Files:**
- Create: `scripts/analyze_draft.py`
- Test: `scripts/test_cli.py` (add)

**Interfaces:**
- Consumes: `extract_text`, `clean_body`, `compute_metrics`, `author_profile.json`.
- Produces: CLI `python scripts/analyze_draft.py <draft> [--profile author_profile.json] [--json] [--raw]`. `--raw` skips the 40-word paragraph filter and the PDF-oriented line filters (for drafts pasted as plain text). Prints a table: metric, draft value, author mean, author range (mean ± 1.5 SD), flag `LOW` / `HIGH` / blank. Then a "Suggested moves" list, one line per flag, from this map:
  - `sent_len_cv` LOW or `adjacent_diff_mean` LOW: "Sentence lengths are too even. Split some long sentences and merge some short neighbours."
  - `short_share` LOW: "Too few short sentences. State some results in under 10 words."
  - `long_share` LOW: "Too few long sentences. Let a few explanations run long, as the author does."
  - `para_len_cv` LOW: "Paragraphs are near-equal. Let them follow the content: some two sentences, some eight."
  - `opener_repeat_rate` HIGH: "Neighbouring sentences start the same way. Vary the openers."
  - `connective_per_1000` HIGH or any `conn_*` HIGH: "Connective overused: <word> at <x> per 1000 vs the author's <y>. Cut or let the logic carry."
  - punctuation keys: "Uses <mark> <more|less> than the author (<x> vs <y> per 1000)."
  - `mattr` HIGH or LOW: "Vocabulary is <more|less> varied than the author's. Repeat the technical term instead of cycling synonyms." / "Reduce repeated filler words."
  - A metric with author SD of 0 is never flagged. Drafts under 8 sentences print "Too short to judge (N sentences); statistics need at least 8." and exit 0 with no flags.

- [ ] **Step 1: Write failing tests:** `test_uniform_draft_flags_low_variation` (profile fixture with `sent_len_cv` mean 0.5 sd 0.05; a draft of 20 identical-length sentences; assert output contains `sent_len_cv` and `LOW` and "too even"); `test_short_draft_notice` (3 sentences; assert "Too short to judge" and exit 0).
- [ ] **Step 2: Run.** Expected: fail.
- [ ] **Step 3: Implement** `scripts/analyze_draft.py`.
- [ ] **Step 4: Run.** Expected: all tests pass.

### Task 3b: Technical-integrity checker (key requirement)

**Files:**
- Create: `scripts/check_integrity.py`
- Test: `scripts/test_integrity.py`

**Interfaces:**
- Produces: `extract_technical(text: str) -> dict[str, collections.Counter]` with categories `numbers`, `citations`, `math`, `crossrefs`, `symbols`, `terms`; CLI `python scripts/check_integrity.py <original> <rewrite>` printing, per category, items missing from and added in the rewrite; exit 0 only when every category matches exactly, else exit 1.
- Numbers are normalised so `4--7`, `4-7` and `4–7` match, and `10 %` matches `10%`. A number spelled at a sentence start in one text and as digits in the other counts as a mismatch (reported, not hidden).

- [ ] **Step 1: Write failing tests:** `test_identical_passes`; `test_changed_number_fails` ("12.4 %" vs "12.5 %"); `test_dropped_citation_fails` ("[3, 7]" vs "[3]"); `test_dropped_term_fails` ("PV/T", "Nd:YAG", "SiC", "heat-transfer coefficient" removed); `test_reworded_prose_passes` (same technical items, sentences split and reordered within a paragraph).
- [ ] **Step 2: Run.** Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: pass.

### Task 4: Layer 7 in SKILL.md and end-to-end check

**Layer 7 must also state (technical integrity):** run `check_integrity.py <original> <rewrite>` after every rewrite; on failure, repair or discard the rewrite, never deliver it; never paraphrase a technical term, named method, material, quantity, condition, or procedural step to move a statistic.

**Files:**
- Modify: `SKILL.md` (frontmatter `allowed-tools` adds `Bash`; `version: 0.4.0`; Process step 2 mentions the measurement; new `## Layer 7: Statistical shape (measure, then match the author)` before `## Output`; Output section adds the before/after table)
- Modify: `README.md` (short "Statistical profile" section: the three commands)

**Layer 7 must state:**
- When: any draft of 8+ sentences, after Layers 1–6 are applied to the plan but before final text.
- Run `python "<skill dir>/scripts/analyze_draft.py" <draft file> --raw` (write pasted text to a temp file first). If `author_profile.json` is missing, ask the author for a folder of their own papers and run `build_profile.py`; without one, skip Layer 7 and say so.
- Rewrite moves, each tied to a flag (the map in Task 3). Change only flagged dimensions; move toward the author's range, not past it.
- Hard limits: every number, equation, citation, and claim unchanged; Layer 3 preservations still hold; no deliberate errors, no filler added to pad length; clarity wins over any statistic.
- Re-run the analyzer on the rewrite; report before/after values for flagged metrics; one further pass at most.
- Honest framing: this matches the author's own writing; it does not promise any detector result and does not replace disclosure.

- [ ] **Step 1: Edit** `SKILL.md` and `README.md` as above.
- [ ] **Step 2: Held-out check.** Run `analyze_draft.py` on `Renewable Energy 2024.pdf` and `Optics and Laser Tech 2023.pdf` (expected: few flags) and on a ~400-word AI-style academic passage written for the test and saved to the scratchpad (expected: clearly more flags, including sentence-length evenness or connectives). Record both outputs. If the analyzer cannot tell them apart, report that plainly and adjust thresholds or metrics.
- [ ] **Step 3: Rewrite check.** Apply Layer 7 to the AI-style passage, re-run the analyzer, confirm flags drop and that every number and citation in the passage is unchanged (diff the sets of digits and bracketed citations).
