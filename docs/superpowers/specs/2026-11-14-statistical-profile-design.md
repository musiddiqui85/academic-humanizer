# Statistical profile layer: design (approved 2026-11-14)

## Intent
AI-assisted drafts are statistically uniform: sentence and paragraph lengths cluster, sentence shapes
repeat, connectives are overused. Human academic prose is uneven. The skill should measure a draft
against the author's own published writing and rewrite only where the gap is large, so the draft reads
like the author. It is an editing aid; it does not promise any AI-detector outcome and does not replace
venue disclosure.

## Goals
- Build a reusable author profile from the author's pre-2023 papers (22 PDFs, 2012-2022).
- Report, for any draft, where its statistics differ from that profile.
- Add a Layer 7 to SKILL.md: measure, rewrite where the gap is large, re-measure.

## Non-goals / anti-goals
- No detector-score targeting. No token-predictability (perplexity) scoring.
- Never change a number, equation, citation, or claim to move a statistic.
- Never degrade clarity or add errors to look "human".

## Constraints
- Python standard library plus `pdftotext` only (both already installed). No package installs.
- 2023, 2024, 2026 papers are excluded from the baseline (possible AI assistance); they serve as
  held-out test text. `_compressed` duplicates are skipped.

## Approaches considered
1. **Author's own papers as baseline (chosen).** Sounds like the author; fits Layer 5 voice matching.
2. Generic human-academic profile. Needs no samples, but the target is an average of many authors.
3. Token-predictability scoring. Needs a local language model; small gain over the measures below.

## Parts
- `scripts/textstats.py`: shared code. PDF/text cleaning (drop references, captions, equations, tables,
  headers, short lines), sentence splitting with abbreviation handling, and the metrics:
  sentence-length mean/SD/coefficient of variation, share of short (<=10 words) and long (>=35 words)
  sentences, adjacent-sentence length difference, paragraph-length CV, repeated-opener rate, connective
  rate per 1000 words (per connective and total), punctuation per 1000 words (comma, semicolon, colon,
  parentheses), vocabulary spread (moving-average type-token ratio).
- `scripts/build_profile.py`: runs the metrics over each baseline paper, stores per-metric mean and SD
  across papers in `author_profile.json`.
- `scripts/analyze_draft.py`: runs the metrics on a draft (.txt, .md, .tex, .pdf, .docx) and prints a gap
  report: each metric, the draft value, the author's range, and a flag when outside mean +/- 1.5 SD.
- `SKILL.md` Layer 7 and `allowed-tools` gains Bash.

## Technical integrity (key requirement, added by the author 2026-11-14)
Technical details must remain intact through any rewrite. This is enforced by a script, not by a promise:
- `scripts/check_integrity.py <original> <rewrite>` extracts from both texts and compares as multisets:
  numbers (with sign, decimals, exponents, ranges, percent), units attached to numbers, citations
  (`[3]`, `[3, 7-9]`, `\cite{key}`, `(Author, 2019)`, `Author et al. (2019)`), inline and display math
  (`$...$`, `\(...\)`, `\[...\]`, LaTeX environments), cross-references (Fig./Table/Eq./Section N),
  acronyms and symbols (all-caps tokens, tokens mixing letters and digits, Greek letters, sub/superscript
  tokens), and hyphenated technical terms.
- Any item missing from, or new in, the rewrite is listed and the script exits non-zero.
- Layer 7 must run it after every rewrite. A failed check means the rewrite is repaired or discarded; it
  is never delivered with a failed check. Technical terms, named methods, materials, quantities,
  conditions, and procedural steps are never paraphrased, reordered in meaning, or dropped to move a
  statistic.

## Left to the builder
Exact cleaning heuristics, thresholds, report wording.

## Known limits
Papers are co-authored, so the profile is the group's published voice. It is dominated by 2012-2019
writing.
