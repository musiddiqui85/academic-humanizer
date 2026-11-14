# Author voice and manuscript guidelines: design and plan (approved 2026-11-14)

## Intent
The skill should write in the author's own voice (phrasing, person, passive use, figure-reference
habits), captured from their published papers, and follow academic manuscript guidelines for structure
and section content. The author chose: **voice wins on style; guidelines decide structure.**

## Goals
- `scripts/extract_voice.py` builds a personal `author_voice.md` (git-ignored) from the same baseline
  papers as the statistical profile.
- SKILL.md gains a manuscript-guidelines layer (Layer 8) and an explicit precedence rule.
- Phrases on the Layer 1–2 tell lists that the author really uses are kept at up to the author's own
  rate, not stripped.

## Non-goals / anti-goals
- Voice never licenses an unsupported claim: Layers 2.1, 2.2, 4 stay governed by evidence.
- Technical integrity (Layer 7.4) outranks everything.
- No other author's voice is substituted. No detector targeting.

## Approaches considered
1. **Voice wins on style, guidelines on structure (chosen by the author).**
2. Guidelines always win: tighter text, but strips the author's real phrases.
3. Voice only, no guidelines: keeps structural faults of a draft.

## Parts
- `scripts/extract_voice.py <folder> [--max-year 2022] [--out author_voice.md]`:
  - `sectioned_paragraphs(path) -> dict[str, list[str]]` with keys `introduction`, `methods`,
    `results`, `conclusions`, `other`, from numbered headings classified by keyword.
  - `voice_stats(papers: list[dict[str, list[str]]]) -> dict` computing: person (share of sentences
    with we/our, "the authors"), passive-like share, present vs past auxiliaries, each overall and by
    section; 3-word sentence openers used in >= 3 papers; 3- to 5-word phrases used in >= 30% of papers
    (minimum 3 papers), longest form kept; rate per 10,000 words of every `TELL_PHRASES` item (the
    Layer 1–2 watch-lists) with paper counts; figure/table reference patterns; reporting and hedging
    verbs; British vs American spelling pairs; example first sentences of introductions and
    conclusions and example objective statements (up to 8 each).
  - `render_markdown(stats) -> str` and the CLI. Papers after `--max-year` and `_compressed`
    duplicates are skipped, as in `build_profile.py`.
- SKILL.md: Layer 5 reads `author_voice.md` when present; new `## Layer 8: Manuscript guidelines`
  (section-by-section, journal guide for authors overrides); new `## Precedence` section; Layer 3 "we"
  note defers to the voice profile. Version 0.5.0.
- README: one paragraph and the command. `.gitignore`: `author_voice.md`.

## Tests (`scripts/test_voice.py`)
- person and passive shares on a constructed text; a tell phrase's rate and paper count;
- a phrase in 2 of 3 papers is listed and one in 1 of 3 is not;
- section classification of headings ("1. Introduction", "3. Results and discussion", "5. Conclusions");
- CLI writes the file, honours `--max-year`, and names skipped files.

## Execution
Inline, same branch, commit per part. (The author approved the design and chose inline execution in
conversation.)
