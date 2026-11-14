---
name: academic-humanizer
version: 0.5.0
description: |
  Improve the clarity and voice of AI-assisted academic writing (papers, theses, rebuttals) and
  funding proposals (NSF Project Summary/Description, NIH Specific Aims): preserve scholarly
  conventions, match claims to evidence (and, for proposals, claims to feasibility), and match the
  author's own voice, including the statistical shape of their prose (sentence and paragraph length
  spread, connective and punctuation rates) and their phrasing habits, both measured from their own
  published papers, and follow section-by-section manuscript guidelines. It never
  changes a number, result, citation, or technical detail, and it is not for evading AI-use
  disclosure. Use when editing AI-assisted academic prose or grant proposals.
license: MIT
compatibility: claude-code codex morphmind opencode
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion]
---

# Academic Humanizer

Improve the clarity and voice of AI-assisted *academic* writing while keeping the precise,
evidence-bound voice that scholarship requires and matching the author's own style. It preserves every
number, result, and citation, and it is not a tool for evading AI-use disclosure.

## When to use
Editing or reviewing academic prose: paper sections, abstracts, rebuttals, related work, and **funding
proposals** (NSF Project Summary/Description, NIH Specific Aims, fellowship and foundation proposals;
see Layer 6). **Not** for blogs, marketing, or personal essays, and **never** inject opinion, humor, or
first-person "personality" into a manuscript. For technical writing, neutral and precise *is* the human
voice. One caveat for proposals: their register is different from a paper's, since they are sold on
vision and feasibility, so the ambition language a paper would trim is appropriate there; apply Layer 6,
not the paper layers' stricter trimming, to vision statements.

## Core principle
Academic writing already has a correct human voice: neutral, precise, third-person plural ("we"), every
claim tied to its evidence. The job is to (1) strip the AI *tells* without casualizing, and (2) enforce
the discipline a general humanizer misses: **every claim earns its number, figure, or citation, and no
verb is stronger than its evidence.**

## Precedence (when rules pull in different directions)
1. **Technical integrity and claim-evidence** (Layers 3, 4, 7.4) always win. Nothing below may change a
   number, unit, symbol, citation, or the strength of a claim.
2. **The target journal's guide for authors**, where it is binding: length limits, required sections,
   reference style, and person or voice if the journal mandates one.
3. **Manuscript guidelines** (Layer 8) decide structure: what each section contains and in what order.
4. **The author's voice** (Layer 5, `author_voice.md`) decides phrasing and style: person, passive use,
   tense habits, signature phrases, figure-reference style, spelling variant. **Voice wins on style.**
   A phrase that Layers 1 and 2 list as a tell is kept, up to the author's own rate, when the voice
   profile shows it is the author's habit; only phrases the author never or rarely used are removed.
5. **Tell removal** (Layers 1 and 2) applies to everything the voice profile does not claim.

Voice never licenses a claim: an over-claiming verb (2.1) or significance hype (2.2) needs evidence
however often the author has used the word.

## Process
1. **Read** the manuscript and any author writing sample; note the document type (paper vs. funding
   proposal) and the target venue or funding agency. For proposals, also apply Layer 6 and preserve
   appropriate vision. If `author_voice.md` exists in this skill's folder, read it now (Layer 5).
2. **Audit** (do not edit yet): list each detected pattern with its location and proposed fix, and each
   empirical claim's evidence status. For drafts of 8 or more sentences, also **measure** the draft's
   statistical shape against the author's profile (Layer 7).
3. **Rewrite**: same structure and content, all claims and citations preserved, tells removed, over-claims
   matched to evidence, legitimate hedging kept, and the flagged statistical dimensions moved toward the
   author's range.
4. **Verify**: run the technical-integrity check on original vs. rewrite (Layer 7.4). A rewrite that
   fails is repaired or discarded, never delivered. Then re-measure.
5. **Report**: cleaned text plus a short change log (patterns removed, claims softened or given evidence
   pointers, voice notes, before/after statistics, integrity result). Cover everything the original
   covered: if it had five paragraphs' worth of content, so does the rewrite.

---

## Layer 1: General AI-tell catalog
Scan for and fix the general patterns, subject to the academic exceptions in Layer 3:
inflated significance ("marking a pivotal moment"); superficial "-ing" tails that fake depth
("..., highlighting..."); promotional/figurative language ("rich", "vibrant", "groundbreaking");
vague attributions ("experts argue" with no cite); AI vocabulary (*delve, underscore, intricate,
tapestry, testament, landscape (abstract), pivotal, showcase, foster, leverage (filler), realm,
seamless*); copula avoidance ("serves as" -> "is"); negative parallelisms ("not just X, but Y");
rule-of-three padding; elegant variation (cycling synonyms for one referent); filler
("it is worth noting that", "in order to"); **overlong, clause-stacked sentences (split them; see 2.11)**;
and **em-dashes (remove entirely; recast with commas, colons, parentheses, or separate sentences)**.

**Before:** *Additionally, an enduring testament to the method's value is its ability to delve into
intricate dependencies, showcasing a seamless integration that underscores its pivotal role.*
**After:** *The method also captures higher-order dependencies, which the baselines miss (Table 2).*

---

## Layer 2: Academic AI tells (remove or fix)

### 2.1 Over-claiming verbs
Empirical work *shows* and *provides evidence*; it does not *prove* or *demonstrate* universal truths.
**Watch:** demonstrate, prove, establish, confirm, guarantee; "significantly" with no test/number.
**Before:** *We prove that our method significantly outperforms all prior approaches.*
**After:** *Our method improves held-out accuracy by 4--7 points over the strongest prior approach
(Table 3); the gain is significant at p < 0.01 by a paired test.*

### 2.2 Significance hype
**Watch:** paves the way for, a crucial/pivotal step toward, has the potential to revolutionize, opens
new avenues, sheds light on, of paramount importance, bridges the gap.
**Before:** *This work paves the way for a new paradigm and sheds light on a problem of paramount
importance.*
**After:** *This work addresses one failure mode of prior methods: error accumulation under long-horizon
rollout (Section 4).*

### 2.3 Empty intensifiers
**Watch:** extensive/comprehensive/thorough experiments, a wide range of, numerous, various.
**Before:** *We conduct extensive experiments on a wide range of datasets.*
**After:** *We evaluate on three datasets (ImageNet, CIFAR-100, and iNaturalist).*

### 2.4 Novelty padding
**Watch:** "novel" used more than once per section; "to the best of our knowledge"; "for the first time".
**Before:** *We propose a novel framework and, to the best of our knowledge, are the first to study this.*
**After:** *We study online calibration under delayed labels, which prior calibration work (offline) does
not address.*

### 2.5 Formulaic openers
**Watch:** "In recent years, X has attracted increasing attention"; "With the rapid development of...";
"Despite recent advances,...".
**Before:** *In recent years, tabular deep learning has attracted increasing attention.*
**After:** *Tabular deep learning has a structural limitation: most models discard feature-type metadata
and must relearn it from data.*

### 2.6 Connective overuse
Do not start consecutive sentences with Moreover/Furthermore/Additionally/In particular; let logic carry.
**Before:** *Moreover, the method is fast. Furthermore, it is simple. Additionally, it scales.*
**After:** *The method is fast and simple, and it scales to one million rows (Section 5).*

### 2.7 Contribution-list cliches
Each contribution names a *specific* result, not a restatement of the abstract.
**Before:** *Our contributions are: (1) a novel method; (2) extensive experiments; (3) strong results.*
**After:** *We (1) introduce a metadata-aware encoder that reaches 0.91 AUROC vs 0.86 for the strongest
baseline; (2) show it stays within 2 points under 20% label noise where the baseline drops 9; (3) release
the benchmark.*

### 2.8 Citation dumping
Cite the one or two works that matter and say why, not a bracketed list.
**Before:** *Many methods exist [3, 7, 9, 12, 15].*
**After:** *The closest prior method is TabNet [7], which encodes all features jointly; we instead
condition on feature-type metadata.*

### 2.9 Hedging-by-vagueness
**Watch:** somewhat, relatively, fairly, to some extent, quite. Quantify or cut.
**Before:** *Performance is somewhat better and relatively robust.*
**After:** *Accuracy is 3 points higher and varies by less than 1 point across five seeds.*

### 2.10 Boilerplate emphasis
**Watch:** "It is worth noting that", "It should be emphasized that", "Notably,", "Importantly,".
If it matters, the sentence shows it.
**Before:** *It is worth noting that, importantly, the gain holds across scenarios.*
**After:** *The gain holds across all three scenarios (Table 4).*

### 2.11 Overlong, clause-stacked sentences
AI favors long sentences that chain three or four clauses with commas and "which", "that", "while", "with".
Split them: one idea per sentence, and cut subordinate clauses that carry no weight. **Watch:** sentences
past ~30 words, or with 3+ subordinate clauses.
**Before:** *Existing methods, though promising, are largely empirical, with unclear principles
underpinning their behavior, which limits their reliability and further progress.*
**After:** *Existing methods stay empirical. Their principles are unclear, which limits reliability and
progress.*

---

## Layer 3: Preserve these (do NOT over-correct)
A general humanizer flattens legitimate scholarly constructs. Keep them.

- **Evidence-tied hedging is correct and required.** Keep "suggests", "is consistent with", "we
  hypothesize that", "may indicate", "appears to" when the claim is genuinely uncertain.
  *Wrong fix:* turning *"the results suggest X"* into *"the results prove X"*: this manufactures
  over-claiming. Keep the calibrated verb.
- **Passive voice** is fine when the actor is irrelevant: *"Samples were normalized to total protein."*
- **First-person plural "we"** is standard; do not rewrite to avoid it. The exception is an author
  whose voice profile shows they do not write in the first person: then do not introduce "we" (Layer 5).
- **Semicolons and an occasional triple** are fine in moderation. Em-dashes are the exception: remove
  them entirely (Layer 1), recasting with commas, colons, parentheses, or separate sentences.
- **Formal definitions, named methods/metrics, technical terms, equations, and symbols** stay verbatim.
- **Never invent, drop, or alter a number, equation, or citation.** Same content; preserve every cite key.

---

## Layer 4: Claim-evidence discipline
For every empirical claim, check (a) is it backed by a number, figure, table, or citation in the text,
and (b) does the verb match the strength of that evidence?

- **Unbacked claim -> add the evidence pointer or soften.**
  *Before:* *Our method is more robust.*  *After:* *Our method's accuracy drops by 2 points under
  distribution shift, versus 11 points for the baseline (Figure 3).*
- **Verb stronger than evidence -> downgrade.**
  *Before:* *This demonstrates that our method is universally superior.*
  *After:* *On these three datasets, our method matches or exceeds the strongest baseline (Table 2).*
- **Vague magnitude -> a number or RANGE, attributed.**
  *Before:* *a large improvement.*  *After:* *a 2--6% improvement in balanced accuracy over the strongest
  baseline.*
  Prefer ranges (e.g., "2--6%") over single averaged values unless the averaging method is stated, and
  attribute each number to its method, metric, and baseline. When comparing, lead with the comparison
  against the strongest competitor, not the trivial baseline.

---

## Layer 5: Voice and venue matching
If the author supplies prior papers, read a sample first and note sentence rhythm, connective habits,
level and placement of hedging, how they open sections, notation, and recurring phrasings, then match
them. Match the venue's register too (e.g., ICLR/NeurIPS: terse, direct, results-forward; Nature/PNAS:
more expository). Absent a sample, default to clean, precise, venue-appropriate prose, not the casual,
opinionated voice of a general-purpose humanizer.

### 5.1 The author voice profile
If `<skill>/author_voice.md` exists, it is the measured record of how this author writes, built from
their own papers. Read it before auditing and write to it. If it is missing and the author can supply a
folder of their own papers, build it once (the year is read from each filename):

```
python "<skill>/scripts/extract_voice.py" "<folder of the author's papers>" --max-year 2022
```

How to apply it:
- **Person and voice.** Follow the profile's first-person and passive rates, section by section. If the
  author almost never writes "we", do not introduce it: use the passive or an inanimate subject ("The
  model predicts ...", "In the current work, ... was developed"). Do not convert the author's passives
  to active voice wholesale.
- **Signature phrases and sentence openers.** Prefer the author's own recurring phrases to a synonym
  they never use, at about the listed rate and never above it. A short passage gets a phrase once or
  not at all.
- **Phrases on the tell lists.** The profile sorts every Layer 1 and Layer 2 watch-list phrase into
  three groups. *Habits*: keep, up to the author's rate per 10,000 words. *Rare*: avoid, at most once
  in a manuscript. *Never used*: always remove. This replaces blanket removal for this author.
- **Figures and tables.** Refer to them the way the author does ("Fig. 3 shows ...", "... is shown in
  Fig. 3"), in the abbreviation the journal requires.
- **Reporting and hedging verbs, spelling.** Use the author's usual verbs and spelling variant.
- **Examples.** The profile ends with real opening sentences and objective statements. Use them as
  models of register and construction, not as text to copy.

Limits: the profile governs phrasing only. It does not excuse an unsupported claim, a vague magnitude,
or a missing evidence pointer (Layers 2.1, 2.2, 4), and it never outranks a journal requirement or the
technical-integrity check. The profile usually reflects co-authored papers, so it is the group's
published voice.

## Layer 6: Funding-proposal mode (NSF, NIH)
A proposal is not a paper. It is sold on **vision plus feasibility**, not on finished results, and
reviewers score it. The register shift matters: ambition language that the paper layers would trim
("long-term goal", "pioneer", "transformative", "establish a foundation") is *appropriate and expected*
here, provided a credible plan and evidence back it. So in proposal mode, **do not flatten the vision**;
enforce a different discipline instead: **claim <-> feasibility**.

### 6.1 Know the structure; the score lives in the first pages
Reviewers form a score from the opening, then skim the rest to confirm it. Put most editing effort there.
- **NSF.** A one-page **Project Summary** with the three review-criteria heads spelled out:
  **Overview**, **Intellectual Merit**, **Broader Impacts**, each self-contained. The Project
  Description then opens with **long-term vision -> this proposal's goal -> the gap -> the specific
  thrusts/aims -> the payoff**, ideally within the first 1--2 pages, with one overview figure. Broader
  Impacts must be substantive and integrated, never an afterthought.
- **NIH (R01).** The **Specific Aims page is the whole proposal in one page**, and is the most-read,
  most-decisive page. Standard arc: (1) opening: the problem, what is known, the **gap / critical need**;
  (2) the **long-term goal** and the **central hypothesis** with its rationale; (3) "**The objective of
  this application is...**" plus how the hypothesis was formed; (4) **2--3 Aims**, each a one-line goal +
  a phrase on approach + the expected outcome; (5) a **payoff** paragraph: what changes if it succeeds.
  Then **Significance, Innovation, Approach** as separately scored sections.

### 6.2 First-3-pages primacy (edit these hardest)
By the end of page 1 (NIH Aims) or pages ~2--3 (NSF), the reader must already hold: the **hook** (why it
matters, concretely), the **gap** (what is missing and the cost of the gap), the **central idea** (your
approach in one sentence), the **aims/thrusts** (crisp and parallel), and the **payoff**. If any is
missing or buried, fix that before touching later sections. A reviewer unconvinced by page 3 does not
recover on page 10.

### 6.3 Proposal-specific weak moves to fix
- **Vague importance.** *Watch:* "this is an important/timely problem", "X has many applications".
  **Before:** *Understanding this problem is critically important.*
  **After:** *Without bounds on how measurement noise propagates to diagnosis, clinical models are tuned by
  trial and error, the inefficiency this proposal removes.*
- **Method-as-aim** (an aim naming a technique instead of a question or outcome).
  **Before:** *Aim 2: Apply transfer learning to the dataset.*
  **After:** *Aim 2: Determine whether fusing wearable and lab signals improves early detection, and for
  which patient subgroups it helps or hurts.*
- **Dominoed aims** (Aim 2/3 collapse if Aim 1 fails; reviewers flag this as fragile). *Fix:* phrase
  aims as **parallel and independently valuable**; where one depends on another, state the fallback.
- **Ambition without feasibility.** Every bold claim needs a footing: preliminary data, a prior
  result/publication, a classical theorem you build on, or a collaborator/letter. *Fix:* attach the
  evidence beside the claim ("our preliminary result in Fig. X shows...", "building on a classical minimax
  lower bound...").
- **Boilerplate Broader Impacts / training plan.** *Watch:* "we will mentor students and disseminate via
  talks and papers." *Fix:* make it concrete, enumerated, and tied to the research: specific programs,
  named courses or tools, measurable outreach.
- **Hedged central hypothesis.** The Aims-page hypothesis is a falsifiable commitment, not "we will
  explore whether possibly...". Calibrated hedging belongs in the Approach's interpretation, not the
  central claim.

### 6.4 Preserve and deploy (funded-proposal craft)
These read as strength; keep or add them rather than editing them out.
- **Vision/ambition framing**: a bold long-term goal up front, with this proposal as one principled step
  toward it.
- **Run-in lead-ins for scannability**: bold/italic **Goal:**, **Motivation:**, **Innovation:**,
  *Thrust/Aim N (one-line mission):*. Reviewers skim; visible structure earns time.
- **A concrete running example or protagonist** to make an abstract method vivid and consistent across aims.
- **Sharp challenge/aim statements posed as questions**: a crisp open question reads as a well-posed
  problem (a boxed or set-off question per aim works well).
- **Anchoring novel work in deep, named classical results** to signal rigor and lineage: a known
  inequality, capacity notion, or test that the new method generalizes.
- **Foreground the team's standing as feasibility evidence**: prior funded work, preliminary results,
  publications, collaborators, and demonstration partners belong *early*, as proof the plan is executable.
  A real track record is evidence, not boasting; place it where it de-risks the aims. *(Use only the PI's
  own real, supplied record; never invent funding, results, partners, or letters.)*

### 6.5 Claim <-> feasibility (the proposal analog of Layer 4)
For every aim and promised outcome, check: is the ambition matched by a credible means, such as
preliminary data, a prior method, a classical foundation, a collaborator, or staged de-risking? If yes,
keep the ambitious verb. If no, attach the missing evidence or scale the claim to what the plan supports.
Never invent preliminary results, prior funding, partners, or letters; if the support does not exist, flag
the gap for the author rather than papering over it.

---

## Layer 7: Statistical shape (measure, then match the author)
AI-drafted prose is statistically even: sentences cluster around one length, neighbouring sentences
differ little, paragraphs come out the same size, openers are varied on purpose, and connectives
("Moreover", "Furthermore", "Therefore") start a large share of sentences. An author's own prose is
uneven in its own particular way. Layers 1 to 6 fix words and claims; this layer fixes the shape, and it
does so by **measurement against the author's own published papers**, not by eye and not against a
generic "human" average.

The scripts live in this skill's `scripts/` folder (Python standard library plus `pdftotext`). Call them
with the skill's base directory, shown here as `<skill>`.

### 7.1 The author profile
`<skill>/author_profile.json` holds, for each metric, the mean and spread across the author's papers.
If it is missing, ask the author for a folder of their own papers, then build it once:

```
python "<skill>/scripts/build_profile.py" "<folder of the author's papers>" --max-year 2022
```

The year is read from each filename. `--max-year` keeps the baseline to papers written before
AI-assisted drafting was common; the later papers are left out. If the author has no papers to give,
skip Layer 7 and say so in the report. Do not substitute another author's profile.

### 7.2 Measure the draft
Save the draft text to a file if it was pasted, then:

```
python "<skill>/scripts/analyze_draft.py" "<draft file>" --raw
```

(`--raw` keeps every paragraph; omit it for a full PDF, where captions and references should be
stripped.) The report gives each metric, the draft's value, the author's range (mean ± 1.5 SD), a
`LOW`/`HIGH` flag, and one suggested move per flag. Drafts under 8 sentences are too short to judge;
under about 300 words, treat flags as hints.

### 7.3 Rewrite only what is flagged
Change only the flagged dimensions, and move them **into** the author's range, not past it. Unflagged
dimensions stay as they are.

| Flag | Move |
|---|---|
| Sentence length spread or neighbour change `LOW` | Merge two short related sentences into one long one; split one long sentence so a short one stands alone. Put a short sentence next to a long one. |
| Mean sentence length `LOW` / `HIGH` | Merge related short sentences / split the longest at a clause boundary. |
| Sentence length spread or neighbour change `HIGH` | Even out the extremes: split the longest sentences, and do not set the shortest next to the longest. |
| Long-sentence share `LOW` | Let an explanation, a method description, or a list of conditions run as one long sentence, as the author does. |
| Long-sentence share `HIGH` | Split the longest sentences at a clause boundary; turn a colon or semicolon into a full stop. |
| Short-sentence share `LOW` | State a result or a transition in under 10 words. |
| Short-sentence share `HIGH` | Join a short sentence to the sentence it qualifies. |
| Paragraph length spread `LOW` | Let paragraphs follow the content: join two that share a topic, leave a two-sentence paragraph where the point is small. Never pad one to match another. |
| Paragraph length spread `HIGH` | Split the longest paragraph at a change of topic, or join a one-sentence paragraph to its neighbour. |
| Vocabulary spread `LOW` | Cut repeated filler words; leave repeated technical terms alone. |
| Same-word openers `LOW` | Stop forcing variety. If the author starts neighbouring sentences with "The ..." or the subject's name, do the same. |
| Same-word openers `HIGH` | Vary the openers. |
| Sentences opening with a connective `HIGH`, or a connective overused | Delete the connective when the logic is already clear; otherwise move it inside the sentence ("The stress, however, ...") or fold the two sentences together with "and", "but", "so", "which". |
| Punctuation rate `LOW` / `HIGH` | Shift toward the author's habit (more or fewer commas, semicolons, colons, parentheses) only where it reads naturally. |
| Vocabulary spread `HIGH` | Repeat the technical term instead of cycling synonyms (this is also Layer 1's "elegant variation"). |

Hard limits on this layer:
- **Technical details stay intact. This is the first rule of the layer.** Every number, unit, equation,
  symbol, citation, cross-reference, named method, material, condition, and procedural step in the
  original appears in the rewrite, unchanged in value and in meaning. Never paraphrase a technical term
  to move a statistic. Never drop a qualifier ("at 0.05 m/s", "under STC", "for the cooled module") when
  merging or splitting sentences; the qualifier travels with its claim.
- Merging and splitting must not change which claim a citation or a number supports.
- No deliberate errors, no filler added to pad a sentence, no content cut to shorten one.
- Layer 3 still holds: calibrated hedging, passive voice, "we", and definitions stay.
- Clarity wins. If a move would make a sentence harder to follow, leave the flag standing and say so.

### 7.4 Verify, then re-measure
After every rewrite, with the original and the rewrite each saved to a file:

```
python "<skill>/scripts/check_integrity.py" "<original file>" "<rewrite file>"
```

Save both files as UTF-8 text (the script also reads UTF-16, Word, and PDF). Compare like with like:
the passage you were given against your rewrite of that passage, not a whole PDF against a section.

What it compares, and how:
- **Exact counts must match:** numbers (including exponents and signs), quantities (number plus unit),
  math, operators and comparators (`=`, `<`, `>`, `≤`, `≥`, `±`, `+`, minus), citations,
  cross-references, number words ("three", "fourth"), and polarity and direction words ("not",
  "without", "less", "above", "before", "increase"/"decrease" and their kin).
- **Must still be present:** symbols and acronyms (including single letters and Greek), chemical
  element symbols, and hyphenated terms.

Three result levels, all of which you act on:
- **`FAIL`** (exit code 1): a technical item was lost, changed, or added. Repair the rewrite and run
  the check again. A rewrite is never delivered with a failed check.
- **`CHECK`** (exit code 0, headline "PASS, with N CHECK item(s)"): something that is usually harmless
  changed: how many times a symbol or term is mentioned, a hyphen, the order in which the numbers
  appear, or the count of a quantity word ("more", "only", "first"). Read each one against the two
  texts. If a qualifier was dropped ("under STC" now stated once instead of twice) or a number now sits
  with a different quantity, repair it. Otherwise name the item in the report. `--strict` turns every
  CHECK into a FAIL; use it when the author asks for no changes of any kind.
- **`REVIEW words removed / added`**: read both lists. Every removed word must be filler or an AI tell
  (Layers 1 and 2), never a technical term, material, or condition; restore any that is. Every added
  word must add no claim.

Options:
- `--protect <file>`: a glossary of phrases (one per line) that must survive, for multi-word technical
  terms with no hyphen or capital ("thermal stress", "mass flux"). Build one from the passage's key
  terms when the text is dense, or use the author's.
- `--accept word[,word]`: waives a polarity word whose count changed on purpose, for example "not"
  when a rhetorical "not only ... but also" was removed under Layer 1. Use it only for a change you can
  name, and name it in the report. It never applies to numbers, units, symbols, or citations.
- A deliberate Layer 4 change (adding an evidence pointer such as "(Table 3)" at the author's request)
  shows up as an added item. Name each such item in the report; nothing else may differ.

**What the script cannot see, so you must read for it.** A `PASS` means every compared item is intact.
It does not prove the meaning is intact. After a PASS, read the rewrite against the original sentence
by sentence for: a number that moved to a different quantity of the same unit; a citation that now
supports a different claim; a condition or qualifier that moved to a different result; a cause and
effect that were reversed; and a technical term replaced by a near-synonym that kept the same words
elsewhere. Report that you did this read.

Then run `analyze_draft.py` on the rewrite. Report the flagged metrics before and after. Make at most
one further pass; do not chase every flag to zero, since a short passage will not match a whole-paper
average exactly.

### 7.5 What this is and is not
This matches a draft to the author's own published writing so it reads as theirs. It does not target
any AI-detector's score, it cannot promise what a detector will report, and it does not replace the
disclosure a venue requires.

---

## Layer 8: Manuscript guidelines (structure, section by section)
These decide **what each section contains and in what order**. The author's voice (Layer 5) decides how
it is phrased. When the author names a target journal, read its guide for authors and let it override
anything here: word and figure limits, required sections (highlights, graphical abstract, nomenclature,
data availability, CRediT statement), heading style, reference style, and units.

When editing, check the draft against the relevant section below and report gaps. Do not invent content
to fill a gap: flag it for the author (Layer 4 still holds).

### 8.1 Title, abstract, highlights, keywords
- **Title:** names the system, the method, and the main variable or outcome. No "novel", no
  abbreviations the reader must look up, no "A study of".
- **Abstract:** one paragraph, self-contained, within the journal's limit (usually 150 to 250 words).
  Order: the problem in one or two sentences; what was done and how; the main results **with numbers**;
  what they mean. No citations, no undefined abbreviations, no reference to figures or tables, nothing
  that is not in the paper.
- **Highlights** (where required): three to five bullets, each one finding, each within the journal's
  character limit, with a number where there is one.
- **Keywords:** the terms a searcher would use; avoid repeating the title word for word.

### 8.2 Introduction
A funnel, in this order:
1. **Context:** the technology or problem and why it matters, stated concretely.
2. **What is known:** the prior work that bears on this paper, grouped by approach, each group with
   what it found and what it left open. Cite critically (Layer 2.8), not as a list.
3. **The gap:** the specific thing prior work did not do, stated as a limitation of named studies.
4. **This work:** the objective, then what was done, in one or two sentences ("In the current work,
   ..."). State the contribution as a specific result or capability, not as "a novel framework".
5. **Outline** of the paper only if the journal's papers usually have one.

No results in the introduction beyond a one-line statement of the main finding, if the field allows it.

### 8.3 Methods (model, experiment, or both)
- Enough detail for a competent reader to **reproduce** the work: geometry, materials and their
  properties with sources, boundary and operating conditions, software and version, solver settings,
  mesh or time-step independence, instruments and their uncertainty, sample sizes.
- Governing equations numbered, each symbol defined at first use with its unit, assumptions stated
  before the equations that depend on them.
- **Validation:** against what data, under what conditions, with what error metric and value.
- Past tense for what was done; present tense for what the equations and the model state.
- Every parameter value has a source: measured, cited, or assumed (and say which).

### 8.4 Results and discussion
- One finding per paragraph. Open with the figure or table and what it shows, give the numbers, then
  explain the mechanism, then compare with the literature (agreement, disagreement, and why).
- Every figure and table is cited in the text, in order, and the text says what to see in it. Do not
  repeat a table's numbers in prose; state the trend and the key values.
- Quantify: a range or a value with its unit and baseline, not "significantly higher" (Layer 4).
- State conditions with each result (the qualifier travels with the claim).
- Discuss limitations where they bear on a result: model assumptions, range of validity, uncertainty.

### 8.5 Conclusions
- Not a repeat of the abstract. Open with one sentence on what was done, then the main findings, each
  with its number, in order of importance (a numbered or bulleted list if the journal and the author
  use one).
- Only conclusions the results support; nothing new that was not shown in the paper.
- Limitations and the next step in one or two sentences. No hype about future impact (Layer 2.2).

### 8.6 Figures, tables, equations, units, abbreviations, references
- **Captions** are self-contained: what is plotted, under what conditions, what the symbols mean.
  Axes carry quantity and unit.
- **Units:** SI, a space between number and unit ("32.5 °C", "0.05 m/s"), the same unit for the same
  quantity throughout, consistent significant figures.
- **Abbreviations and symbols:** defined at first use in the abstract and again in the body, then used
  consistently. One symbol, one meaning. A nomenclature list if the journal uses one.
- **Equations:** numbered, punctuated as part of the sentence, referred to as the journal prescribes.
- **References:** every citation in the list and every list entry cited; recent work included; the
  journal's style. Never add, drop, or alter a reference (Layer 3).
- **Consistency checks before finishing:** every number in the abstract and conclusions matches the
  results section; every "Fig. N" and "Table N" exists; terminology for the same thing does not change
  between sections.

---

## Output
Return the cleaned text plus a short change report: patterns removed (by type), claims softened or given
evidence pointers, and any voice/venue notes. When Layer 7 ran, add the before/after values of the
flagged statistics and the integrity-check result: the headline, every `CHECK` item with how you
resolved it, any `--accept` or deliberate addition by name, and a statement that you read the rewrite
against the original for the changes the script cannot see. When Layer 8 applied, list the structural
gaps you found for the author to fill. Confirm that no number, equation, citation, or technical term was
altered.
