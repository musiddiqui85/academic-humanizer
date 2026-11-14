"""Capture an author's writing voice from a folder of their own papers.

Usage: python extract_voice.py <folder> [--max-year 2022] [--out author_voice.md]

Writes a Markdown voice profile: person and passive use, tense, recurring sentence openers and
phrases, how often the author uses phrases that appear on the skill's AI-tell lists, figure and
table reference habits, reporting and hedging verbs, spelling variant, and example opening
sentences. The skill reads this file and writes to it ("voice wins on style").
"""
import argparse
import datetime
import math
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import (MAX_SENT_WORDS, SUPPORTED, _HEADING_CUT, clean_body, count_words,  # noqa: E402
                       extract_text, split_sentences)

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "author_voice.md")
MIN_SENTENCES = 20
SECTIONS = ("introduction", "methods", "results", "conclusions", "other")

# Phrases on the skill's Layer 1-2 watch-lists. Their rate in the author's own papers decides
# whether they are the author's habit (keep, up to that rate) or a tell (remove).
TELL_PHRASES = [
    "in order to", "it is worth noting", "it is important to note", "it should be noted",
    "it should be emphasized", "it can be seen", "in recent years", "with the rapid development",
    "despite recent advances", "moreover", "furthermore", "additionally", "in particular",
    "notably", "importantly", "novel", "to the best of our knowledge", "for the first time",
    "significantly", "extensive", "comprehensive", "thorough", "a wide range of", "numerous",
    "various", "pivotal", "crucial", "paramount", "paves the way", "sheds light", "bridges the gap",
    "opens new avenues", "delve", "underscore", "intricate", "tapestry", "testament", "landscape",
    "showcase", "foster", "leverage", "realm", "seamless", "robust", "demonstrate", "prove",
    "establish", "confirm", "guarantee", "somewhat", "relatively", "fairly", "quite",
    "to some extent", "serves as", "plays a crucial role", "plays an important role",
    "state-of-the-art", "cutting-edge", "groundbreaking",
]
REPORTING = ["shows", "show", "showed", "shown", "indicates", "indicate", "indicated", "suggests",
             "suggest", "demonstrates", "reveals", "presents", "presented", "found", "observed",
             "noted", "seen", "concluded", "reported", "obtained", "calculated", "predicted"]
HEDGES = ["may", "might", "could", "appears", "seems", "likely", "approximately", "about",
          "around", "nearly", "roughly", "almost", "generally", "usually", "typically"]
SPELLING = [("modelling", "modeling"), ("behaviour", "behavior"), ("optimisation", "optimization"),
            ("characteris", "characteriz"), ("colour", "color"), ("centre", "center"),
            ("fibre", "fiber"), ("vapour", "vapor"), ("utilis", "utiliz"), ("minimis", "minimiz"),
            ("maximis", "maximiz"), ("analysed", "analyzed")]
_STOP = set("""the of in a to is and for on with as by at that was are be it this an from were has
been which can or not have also these its than their there had but if into such when where while
will would should may each both all any other more most some no only same so then thus over under
between after before during about up out very""".split())

_KEYS = [
    ("introduction", ("introduction", "background")),
    ("conclusions", ("conclusion", "concluding", "summary")),
    ("results", ("result", "discussion", "validation", "parametric", "case stud", "findings")),
    ("methods", ("method", "model", "formulation", "experiment", "material", "procedure", "setup",
                 "approach", "theory", "simulation", "governing", "numerical", "analysis",
                 "design", "fabrication", "characterization", "data")),
]
_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVX]+\.)?\s*([A-Z][A-Za-z ,&/:\-]+)$")
_WE = re.compile(r"\b(?:[Ww]e|[Oo]ur)\b")
_AUTHORS = re.compile(r"\b[Tt]he (?:present )?authors?\b")
_PASSIVE = re.compile(
    r"\b(?:is|are|was|were|been|be|being)\s+(?:\w+ly\s+)?(?:\w+(?:ed|en|wn)|made|done|found|"
    r"used|built|held|kept|set|put|carried|shown|given|taken|seen)\b")
_PRESENT = re.compile(r"\b(?:is|are|has|have|can|does|do)\b")
_PAST = re.compile(r"\b(?:was|were|had|did|could)\b")
_FIG_SHOWS = re.compile(r"^(?:Fig\.?|Figure)\s*\d+[a-z]?(?:\s*\([a-z]\))?\s+"
                        r"(?:shows|presents|illustrates|depicts|compares|gives|displays|plots)\b")
_SHOWN_IN = re.compile(r"\b(?:is|are|as|was|were)\s+(?:shown|presented|illustrated|given|plotted|"
                       r"depicted|summarized|listed)\s+in\s+(?:Figs?\.?|Figures?|Tables?)\b")
_TABLE_SHOWS = re.compile(r"^Table\s*\d+\s+(?:shows|presents|lists|gives|summarizes|compares)\b")
_OBJECTIVE = re.compile(
    r"\b(?:objective|aim|purpose|goal)s?\b.{0,60}\b(?:work|study|paper|research|investigation)\b"
    r"|\b[Ii]n (?:the|this) (?:current|present) (?:work|study|paper)\b")
_ALPHA = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")


def classify_heading(line):
    """Return the section a heading line starts, or None when the line is not a known heading."""
    s = line.strip()
    if not s or len(s) > 70 or s.endswith((".", ",", ";")) and not re.match(r"^\d", s):
        return None
    if re.match(r"^(?:Fig|Figure|Table)\b", s):
        return None
    m = _HEADING.match(s)
    if not m or len(m.group(1).split()) > 8 or len(m.group(1).strip()) < 4:
        return None
    title = m.group(1).lower()
    for key, words in _KEYS:
        if any(w in title for w in words):
            return key
    return None


def sectioned_paragraphs(path):
    """Return {section: [paragraphs]} for one paper."""
    text = unicodedata.normalize("NFKC", extract_text(path))
    is_pdf = path.lower().endswith(".pdf")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n").split("\n")
    for i, line in enumerate(lines):
        if _HEADING_CUT.match(line) and i > len(lines) * 0.3:
            lines = lines[:i]
            break
    chunks, current, buf = [], "other", []
    for line in lines:
        key = classify_heading(line)
        if key:
            chunks.append((current, buf))
            current, buf = key, []
        else:
            buf.append(line)
    chunks.append((current, buf))
    out = {k: [] for k in SECTIONS}
    for key, buf in chunks:
        if buf:
            out[key].extend(clean_body("\n".join(buf), line_paragraphs=is_pdf))
    return out


def _sentences(paragraphs):
    return [s for p in paragraphs for s in split_sentences(p) if count_words(s) <= MAX_SENT_WORDS]


def _person(sents):
    n = len(sents)
    if not n:
        return {"n": 0, "we": 0.0, "authors": 0.0, "passive": 0.0, "present_share": 0.0}
    pres = sum(len(_PRESENT.findall(s)) for s in sents)
    past = sum(len(_PAST.findall(s)) for s in sents)
    return {
        "n": n,
        "we": sum(1 for s in sents if _WE.search(s)) / n,
        "authors": sum(1 for s in sents if _AUTHORS.search(s)) / n,
        "passive": sum(1 for s in sents if _PASSIVE.search(s)) / n,
        "present_share": pres / (pres + past) if pres + past else 0.0,
    }


def voice_stats(papers):
    """papers: list of {section: [paragraphs]}. Return the voice statistics as a dict."""
    n_papers = len(papers)
    by_section = {k: [] for k in SECTIONS}
    all_sents = []
    opener_count, opener_papers = Counter(), Counter()
    gram_count, gram_papers = Counter(), Counter()
    tell_count, tell_papers = Counter(), Counter()
    report, hedge, spell = Counter(), Counter(), Counter()
    figures = Counter()
    intro_first, concl_first, objectives = [], [], []
    n_words = 0

    for paper in papers:
        p_openers, p_grams, p_sents = set(), set(), []
        for key in SECTIONS:
            sents = _sentences(paper.get(key, []))
            by_section[key].extend(sents)
            p_sents.extend(sents)
        all_sents.extend(p_sents)
        for s in p_sents:
            words = [w.lower() for w in _ALPHA.findall(s)]
            n_words += len(words)
            if len(words) >= 3:
                op = " ".join(words[:3])
                opener_count[op] += 1
                p_openers.add(op)
            for size in (3, 4, 5):
                for i in range(len(words) - size + 1):
                    gram = words[i:i + size]
                    if all(w in _STOP for w in gram):
                        continue
                    g = " ".join(gram)
                    gram_count[g] += 1
                    p_grams.add(g)
            if _FIG_SHOWS.match(s):
                figures["fig_n_shows"] += 1
            if _SHOWN_IN.search(s):
                figures["shown_in_fig"] += 1
            if _TABLE_SHOWS.match(s):
                figures["table_n_shows"] += 1
            figures["abbrev_fig"] += len(re.findall(r"\bFigs?\.", s))
            figures["full_figure"] += len(re.findall(r"\bFigures?\b", s))
            for w in words:
                if w in REPORTING:
                    report[w] += 1
                if w in HEDGES:
                    hedge[w] += 1
        opener_papers.update(p_openers)
        gram_papers.update(p_grams)
        low = " ".join(p_sents).lower()
        for t in TELL_PHRASES:
            c = len(re.findall(r"\b" + re.escape(t) + r"\w*", low)) if " " not in t else \
                len(re.findall(r"\b" + re.escape(t) + r"\b", low))
            tell_count[t] += c
            if c:
                tell_papers[t] += 1
        for pair in SPELLING:
            for stem in pair:
                spell[stem] += len(re.findall(r"\b" + stem, low))
        intro = _sentences(paper.get("introduction", [])[:1])
        if intro:
            intro_first.append(intro[0])
        concl = _sentences(paper.get("conclusions", [])[:1])
        if concl:
            concl_first.append(concl[0])
        for s in p_sents:
            if _OBJECTIVE.search(s):
                objectives.append(s)
                break

    min_papers = max(2, math.ceil(0.3 * n_papers))
    openers = [{"opener": k, "count": v, "papers": opener_papers[k],
                "per_1000_sentences": 1000.0 * v / max(len(all_sents), 1)}
               for k, v in opener_count.most_common() if opener_papers[k] >= min(3, n_papers)][:30]

    cands = [(g, c, gram_papers[g]) for g, c in gram_count.items() if gram_papers[g] >= min_papers]
    cands.sort(key=lambda x: (-len(x[0].split()), -x[1]))
    kept = []
    for g, c, p in cands:
        if any(g in k[0] and k[1] >= 0.7 * c for k in kept):
            continue
        kept.append((g, c, p))
    kept.sort(key=lambda x: (-x[2], -x[1]))
    phrases = [{"phrase": g, "count": c, "papers": p,
                "per_10k": 10000.0 * c / max(n_words, 1)} for g, c, p in kept[:60]]

    per10k = 10000.0 / max(n_words, 1)
    return {
        "n_papers": n_papers, "n_sentences": len(all_sents), "n_words": n_words,
        "person": dict({"overall": _person(all_sents)},
                       **{k: _person(by_section[k]) for k in SECTIONS}),
        "openers": openers,
        "phrases": phrases,
        "tells": {t: {"count": tell_count[t], "papers": tell_papers[t],
                      "per_10k": tell_count[t] * per10k} for t in TELL_PHRASES},
        "figures": dict(figures),
        "reporting": {w: report[w] * per10k for w in REPORTING if report[w]},
        "hedges": {w: hedge[w] * per10k for w in HEDGES if hedge[w]},
        "spelling": [(a, spell[a], b, spell[b]) for a, b in SPELLING if spell[a] or spell[b]],
        "examples": {"introduction": intro_first[:8], "conclusions": concl_first[:8],
                     "objectives": objectives[:8]},
    }


def _pct(x):
    return f"{100 * x:.1f}%"


def _clip(s, n=300):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " ..."


def render_markdown(st):
    n = st["n_papers"]
    L = []
    L.append("# Author voice profile")
    L.append("")
    L.append(f"Built {datetime.date.today().isoformat()} from {n} papers "
             f"({st['n_sentences']} sentences, {st['n_words']} words) by `scripts/extract_voice.py`.")
    L.append("")
    L.append("How to use this file: write and edit in this voice. Use each habit at about the rate "
             "shown, never more often. Rates are the author's own averages; a short passage will "
             "not hit them exactly. This file governs phrasing and style only. It never licenses a "
             "claim the evidence does not support, and it never overrides technical accuracy.")
    L.append("")
    L.append("## Person and voice")
    L.append("")
    L.append("| Section | Sentences | With \"we\"/\"our\" | With \"the authors\" | Passive | "
             "Present-tense share of auxiliaries |")
    L.append("|---|---|---|---|---|---|")
    for key in ("overall", "introduction", "methods", "results", "conclusions"):
        p = st["person"][key]
        if p["n"]:
            L.append(f"| {key} | {p['n']} | {_pct(p['we'])} | {_pct(p['authors'])} | "
                     f"{_pct(p['passive'])} | {_pct(p['present_share'])} |")
    o = st["person"]["overall"]
    L.append("")
    if o["we"] < 0.03:
        L.append(f"- First person is close to absent ({_pct(o['we'])} of sentences). Do not "
                 "introduce \"we\"; use the passive or an inanimate subject (\"The model predicts\", "
                 "\"In the current work, ... was developed\").")
    else:
        L.append(f"- \"We\"/\"our\" appears in {_pct(o['we'])} of sentences; keep it near that rate.")
    L.append(f"- About {_pct(o['passive'])} of sentences contain a passive construction. Keep the "
             "passive where the author would use it; do not convert it to active voice wholesale.")
    L.append("- Tense: the present-tense share above shows where the author narrates in the present "
             "(higher) or the past (lower). Follow it per section.")
    L.append("")
    L.append("## Sentence openers")
    L.append("")
    L.append("First three words of a sentence, used in at least three papers. Digits are dropped, "
             "so \"fig shows the\" stands for \"Fig. 3 shows the\".")
    L.append("")
    L.append("| Opener | Uses | Papers | Per 1000 sentences |")
    L.append("|---|---|---|---|")
    for x in st["openers"]:
        L.append(f"| {x['opener']} | {x['count']} | {x['papers']} | {x['per_1000_sentences']:.1f} |")
    L.append("")
    L.append("## Signature phrases")
    L.append("")
    L.append(f"Phrases of three to five words found in at least {max(2, math.ceil(0.3 * n))} of the "
             f"{n} papers. Prefer these to a synonym the author never uses.")
    L.append("")
    L.append("| Phrase | Uses | Papers | Per 10,000 words |")
    L.append("|---|---|---|---|")
    for x in st["phrases"]:
        L.append(f"| {x['phrase']} | {x['count']} | {x['papers']} | {x['per_10k']:.1f} |")
    L.append("")
    L.append("## Phrases on the tell lists")
    L.append("")
    L.append("The skill's Layers 1 and 2 remove these as AI tells. Voice wins on style: a phrase the "
             "author really uses is **kept, up to the author's own rate**. A phrase the author never "
             "or almost never used stays a tell and is removed. Over-claiming verbs and significance "
             "hype still need evidence whatever the rate (Layers 2.1, 2.2, 4).")
    L.append("")
    used = sorted(((t, v) for t, v in st["tells"].items() if v["count"]),
                  key=lambda kv: -kv[1]["per_10k"])
    habit = [(t, v) for t, v in used if v["papers"] >= max(2, math.ceil(0.25 * n))]
    rare = [(t, v) for t, v in used if (t, v) not in habit]
    never = [t for t, v in st["tells"].items() if not v["count"]]
    L.append("**The author's habits (keep, up to this rate):**")
    L.append("")
    L.append("| Phrase | Uses | Papers | Per 10,000 words |")
    L.append("|---|---|---|---|")
    for t, v in habit:
        L.append(f"| {t} | {v['count']} | {v['papers']} | {v['per_10k']:.1f} |")
    L.append("")
    if rare:
        L.append("**Rare in the author's papers (avoid; at most once in a manuscript):** "
                 + ", ".join(f"{t} ({v['count']})" for t, v in rare) + ".")
        L.append("")
    if never:
        L.append("**Never used by the author (always remove):** " + ", ".join(never) + ".")
        L.append("")
    f = st["figures"]
    L.append("## Figures and tables")
    L.append("")
    L.append(f"- \"Fig. N shows ...\" as a sentence opening: {f.get('fig_n_shows', 0)} uses.")
    L.append(f"- \"... is/are shown in Fig. N\": {f.get('shown_in_fig', 0)} uses.")
    L.append(f"- \"Table N shows/lists ...\" as a sentence opening: {f.get('table_n_shows', 0)} uses.")
    L.append(f"- Abbreviation: \"Fig.\" {f.get('abbrev_fig', 0)} times, \"Figure\" "
             f"{f.get('full_figure', 0)} times. Follow the target journal's form; otherwise use the "
             "author's more frequent one.")
    L.append("")
    L.append("## Reporting and hedging verbs (per 10,000 words)")
    L.append("")
    L.append("- Reporting: " + ", ".join(
        f"{w} {v:.1f}" for w, v in sorted(st["reporting"].items(), key=lambda kv: -kv[1])) + ".")
    L.append("- Hedging: " + ", ".join(
        f"{w} {v:.1f}" for w, v in sorted(st["hedges"].items(), key=lambda kv: -kv[1])) + ".")
    L.append("")
    if st["spelling"]:
        L.append("## Spelling variant")
        L.append("")
        for a, ca, b, cb in st["spelling"]:
            L.append(f"- {a}: {ca}, {b}: {cb}")
        L.append("")
        L.append("Use the more frequent variant unless the target journal requires the other.")
        L.append("")
    L.append("## Example sentences from the author's papers")
    L.append("")
    for title, key in (("How introductions open", "introduction"),
                       ("How the objective is stated", "objectives"),
                       ("How conclusions open", "conclusions")):
        if st["examples"][key]:
            L.append(f"**{title}:**")
            L.append("")
            for s in st["examples"][key]:
                L.append(f"- {_clip(s)}")
            L.append("")
    return "\n".join(L) + "\n"


def file_year(name):
    years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", name)
    return int(years[-1]) if years else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder")
    ap.add_argument("--max-year", type=int, default=2022)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    if not os.path.isdir(args.folder):
        print(f"error: not a folder: {args.folder}", file=sys.stderr)
        return 2

    papers, used = [], []
    for name in sorted(os.listdir(args.folder)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in SUPPORTED or stem.endswith("_compressed"):
            continue
        year = file_year(stem)
        if year is None:
            print(f"warning: skipped {name}: no year in filename", file=sys.stderr)
            continue
        if year > args.max_year:
            continue
        try:
            sec = sectioned_paragraphs(os.path.join(args.folder, name))
        except Exception as exc:
            print(f"warning: skipped {name}: could not read ({exc})", file=sys.stderr)
            continue
        n_sent = sum(len(_sentences(sec[k])) for k in SECTIONS)
        if n_sent < MIN_SENTENCES:
            print(f"warning: skipped {name}: too little text ({n_sent} sentences)", file=sys.stderr)
            continue
        papers.append(sec)
        used.append(name)

    if not papers:
        print("error: no usable papers found", file=sys.stderr)
        return 1
    md = render_markdown(voice_stats(papers))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Voice profile built from {len(papers)} papers -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
