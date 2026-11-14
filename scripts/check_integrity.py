"""Verify that a rewrite kept every technical detail of the original.

Usage: python check_integrity.py <original> <rewrite> [--protect glossary.txt]

Compares numbers, quantities (number + unit), math, citations, cross-references, symbols and
acronyms, and hyphenated technical terms. Exit code 0 = PASS, 1 = FAIL, 2 = usage error.
A rewrite that fails must be repaired or discarded, never delivered.
"""
import argparse
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import extract_text  # noqa: E402

STRICT = ("numbers", "quantities", "math", "citations")   # exact counts must match
PRESENCE = ("crossrefs", "symbols", "terms")              # every item must still appear
CATEGORIES = STRICT + PRESENCE

_UNITS = sorted("""
% °C °F K m cm mm µm μm um nm km kg g mg µg s ms min h hr Hz kHz MHz GHz N kN MN Pa kPa MPa GPa
bar mbar J kJ MJ W mW kW MW GW Wh kWh MWh V mV kV A mA Ω ohm mol mmol L mL ml eV keV rpm wt% vol%
at% ppm dB rad deg suns sun cP
""".split(), key=len, reverse=True)
_U = r"(?:" + "|".join(re.escape(u) for u in _UNITS) + r")(?:\^?-?\d|[²³])?"
_UNIT = re.compile(r"\s?(" + _U + r"(?:\s?[/·]\s?" + _U + r"|\s" + _U + r"(?![A-Za-z]))*)(?![A-Za-z])")
_NUM = re.compile(
    r"\d+(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?(?:\s*[×x]\s*10\s*\^?\s*\{?-?\d+\}?)?(?:[eE][-+]?\d+)?")
_MATH = [
    re.compile(r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}.+?\\end\{\1\*?\}", re.DOTALL),
    re.compile(r"\$\$.+?\$\$", re.DOTALL),
    re.compile(r"\\\[.+?\\\]", re.DOTALL),
    re.compile(r"\\\(.+?\\\)", re.DOTALL),
    re.compile(r"\$[^$\n]+\$"),
]
_CITE_TEX = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
_CITE_NUM = re.compile(r"\[\s*(\d+(?:\s*[-,]\s*\d+)*)\s*\]")
_YEAR = r"((?:19|20)\d{2}[a-z]?)"
_NAME = r"([A-Z][A-Za-z'’]+(?:-[A-Z][A-Za-z'’]+)?)"
_CITE_AUTHOR = [
    re.compile(_NAME + r"\s+et al\.?,?\s*[(\[]?" + _YEAR + r"[)\]]?"),
    re.compile(_NAME + r"\s+(?:and|&)\s+[A-Z][A-Za-z'’-]+,?\s*[(\[]?" + _YEAR + r"[)\]]?"),
    re.compile(_NAME + r"\s*\(" + _YEAR + r"\)"),
    re.compile(r"(?<=[(;])\s*" + _NAME + r",\s*" + _YEAR + r"(?=\s*[;)])"),
]
_XREF = re.compile(
    r"\b(Figs?|Figures?|Tables?|Eqs?|Eqns?|Equations?|Sections?|Secs?|Appendix|Appendices|"
    r"Chapters?|Refs?)\.?\s*\(?(\d+(?:\.\d+)*[a-z]?|[A-Z](?![A-Za-z]))\)?")
_XREF_NAMES = {"fig": "fig", "figs": "fig", "figure": "fig", "figures": "fig", "table": "table",
               "tables": "table", "eq": "eq", "eqs": "eq", "eqn": "eq", "eqns": "eq",
               "equation": "eq", "equations": "eq", "section": "section", "sections": "section",
               "sec": "section", "secs": "section", "appendix": "appendix",
               "appendices": "appendix", "chapter": "chapter", "chapters": "chapter",
               "ref": "ref", "refs": "ref"}
_TERM = re.compile(r"\b[A-Za-z]+(?:-[A-Za-z0-9]+)+\b")
_GREEK = re.compile(r"[\u0370-\u03ff]")
_STRIP = ".,;:()[]{}\"'“”‘’!?"
_STOP = set("""
about above after again against almost along also although always among another because before
being below between both cannot could different does doing done during each either enough every
first found from further given have having here however into itself just know less made make many
might more most much must need needs never next often only other others over rather same second
several shall should since some still such than that their them then there these they this those
though three through thus under until upon used uses using very were what when where whether which
while will with within without would been
""".split())


def _norm_dashes(text):
    text = text.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"-{2,}", "-", text)


def _norm_num(raw):
    n = re.sub(r"\s+", "", raw).replace("x10", "×10").replace("{", "").replace("}", "")
    n = re.sub(r"×10(?!\^)", "×10^", n)
    if re.fullmatch(r"\d+(?:,\d{3})+(?:\.\d+)?", n):
        n = n.replace(",", "")
    return n


def _stem(word):
    for suf in ("ings", "ing", "edly", "ed", "es", "ly", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[:-len(suf)]
    return word


def _content_stems(text):
    words = re.findall(r"[a-z]{5,}", text.lower())
    return {_stem(w) for w in words if w not in _STOP}


def extract_technical(text):
    """Return {category: Counter} of the technical items in `text`."""
    out = {c: Counter() for c in CATEGORIES}
    work = _norm_dashes(text)

    def take(pattern, handler):
        nonlocal work

        def repl(m):
            handler(m)
            return " "
        work = pattern.sub(repl, work)

    for pat in _MATH:
        take(pat, lambda m: out["math"].update([re.sub(r"\s+", "", m.group(0))]))

    take(_CITE_TEX, lambda m: out["citations"].update(
        k.strip() for k in m.group(1).split(",") if k.strip()))

    def cite_num(m):
        for part in m.group(1).split(","):
            part = part.strip()
            if "-" in part:
                a, b = (int(x) for x in part.split("-", 1))
                if 0 <= b - a <= 200:
                    out["citations"].update(str(i) for i in range(a, b + 1))
                else:
                    out["citations"].update([part])
            elif part:
                out["citations"].update([part])
    take(_CITE_NUM, cite_num)
    for pat in _CITE_AUTHOR:
        take(pat, lambda m: out["citations"].update([f"{m.group(1).lower()} {m.group(2)}"]))

    take(_XREF, lambda m: out["crossrefs"].update(
        [f"{_XREF_NAMES[m.group(1).lower()]} {m.group(2).lower()}"]))

    # Numbers and quantities.
    for m in _NUM.finditer(work):
        start, end = m.span()
        before = work[start - 1] if start else " "
        if before.isalpha() or before in "_^":
            continue  # part of a symbol such as CO2 or x_1
        num = _norm_num(m.group(0))
        if before == "-" and (start < 2 or work[start - 2] in " \t\n(=<>~,:;["):
            num = "-" + num
        unit = _UNIT.match(work, end)
        if unit and unit.group(1).strip():
            u = re.sub(r"\s+", " ", unit.group(1).strip())
            u = re.sub(r"\s?([/·])\s?", r"\1", u)
            out["quantities"].update([f"{num} {u}"])
            if u == "%":
                num += "%"
        out["numbers"].update([num])

    for tok in work.split():
        tok = tok.strip(_STRIP)
        if tok.endswith("'s") or tok.endswith("’s"):
            tok = tok[:-2]
        if len(tok) < 2 or not any(c.isalpha() for c in tok):
            continue
        has_inner_upper = any(c.isupper() for c in tok[1:])
        has_digit = any(c.isdigit() for c in tok)
        if has_inner_upper or has_digit or _GREEK.search(tok) or "_" in tok or "^" in tok:
            out["symbols"].update([tok])

    out["terms"].update(t.lower() for t in _TERM.findall(work))
    return out


def compare(original, rewrite, protect=None):
    """Return (ok, report). ok is False when any technical item was lost, changed, or added."""
    a, b = extract_technical(original), extract_technical(rewrite)
    lines, ok = [], True
    for cat in CATEGORIES:
        missing = a[cat] - b[cat]
        added = b[cat] - a[cat]
        if cat in PRESENCE:
            count_only = {k for k in list(missing) + list(added) if k in a[cat] and k in b[cat]}
            notes = [f"{k} ({a[cat][k]} -> {b[cat][k]})" for k in sorted(count_only)]
            missing = Counter({k: v for k, v in missing.items() if k not in count_only})
            added = Counter({k: v for k, v in added.items() if k not in count_only})
        else:
            notes = []
        if missing or added:
            ok = False
            lines.append(f"FAIL {cat}:")
            if missing:
                lines.append("    missing from rewrite: " + ", ".join(
                    f"{k}" + (f" x{v}" if v > 1 else "") for k, v in sorted(missing.items())))
            if added:
                lines.append("    added in rewrite: " + ", ".join(
                    f"{k}" + (f" x{v}" if v > 1 else "") for k, v in sorted(added.items())))
        else:
            lines.append(f"ok   {cat}: {sum(a[cat].values())} items match")
        if notes:
            lines.append(f"    note, {cat} mention count changed: " + ", ".join(notes))

    for phrase in protect or []:
        pat = re.compile(re.escape(phrase), re.IGNORECASE)
        na, nb = len(pat.findall(original)), len(pat.findall(rewrite))
        if na and not nb:
            ok = False
            lines.append(f"FAIL protected phrase missing from rewrite: {phrase}")
        elif na != nb:
            lines.append(f"    note, protected phrase count changed: {phrase} ({na} -> {nb})")

    sa, sb = _content_stems(original), _content_stems(rewrite)
    gone, new = sorted(sa - sb), sorted(sb - sa)
    if gone:
        lines.append("REVIEW words removed (confirm none is a technical term): " + ", ".join(gone))
    if new:
        lines.append("REVIEW words added (confirm none adds a claim): " + ", ".join(new))
    lines.insert(0, "PASS: technical content intact." if ok else
                 "FAIL: technical content changed. Repair or discard the rewrite.")
    return ok, "\n".join(lines)


def _read(path):
    if path.lower().endswith((".pdf", ".docx")):
        return extract_text(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original")
    ap.add_argument("rewrite")
    ap.add_argument("--protect", help="text file of phrases (one per line) that must survive")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for p in (args.original, args.rewrite, args.protect):
        if p and not os.path.isfile(p):
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2
    protect = None
    if args.protect:
        with open(args.protect, encoding="utf-8") as f:
            protect = [line.strip() for line in f if line.strip()]
    ok, report = compare(_read(args.original), _read(args.rewrite), protect)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
