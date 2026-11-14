"""Verify that a rewrite kept the technical details of the original.

Usage: python check_integrity.py <original> <rewrite> [--protect glossary.txt]
                                 [--accept word[,word...]] [--strict]

Three result levels:
  FAIL   a technical item was lost, changed, or added. Exit code 1. Repair or discard the rewrite.
  CHECK  something that is usually harmless changed (how often a symbol is mentioned, the order of
         the numbers, a hyphen). Exit code 0, but each CHECK line must be confirmed by reading.
         --strict turns every CHECK into a FAIL.
  REVIEW lists of ordinary words removed or added, for a human or model to read.

Compared exactly (counts must match): numbers, quantities (number + unit), math, operators and
comparators, citations, cross-references, number words, and polarity/direction words.
Compared by presence (count changes are CHECK): symbols and acronyms, hyphenated terms.

What no word-level check can see: two numbers of the same unit exchanged between two quantities
(reported as a CHECK on order), a citation moved from one claim to another, and a change of
meaning that reuses the same words. Those still need a sentence-by-sentence read.
"""
import argparse
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import extract_text, read_text  # noqa: E402

STRICT = ("numbers", "quantities", "math", "operators", "citations", "crossrefs",
          "number_words", "polarity")
PRESENCE = ("symbols", "terms")
CATEGORIES = STRICT + PRESENCE

_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋", "0123456789+-")
_NEG, _MINUS = "\x01", "\x02"   # markers: negative sign, binary minus operator

_UNITS = sorted("""
% °C °F K m cm mm μm um nm km kg g mg μg s ms μs ns ps min h hr Hz kHz MHz GHz N kN MN Pa kPa MPa
GPa bar mbar atm psi ksi J kJ MJ W mW kW MW GW Wh kWh MWh V mV kV A mA Ω ohm mol mmol L mL ml eV
keV rpm wt% vol% at% ppm dB rad deg suns sun cP lux lm cd
""".split(), key=len, reverse=True)
_U = r"(?:" + "|".join(re.escape(u) for u in _UNITS) + r")(?:\^-?\d)?"
_UNIT = re.compile(r"\s?(" + _U + r"(?:\s?[/·]\s?" + _U + r"|\s" + _U + r"(?![A-Za-z]))*)(?![A-Za-z])")
_NUM = re.compile(r"(?<!\d)\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)"
                  r"|\d+(?:\.\d+)?(?:×10\^[-+]?\d+)?(?:\^[-+]?\d+)?")
_MATH = [
    re.compile(r"\\begin\{(equation|align|gather|multline|eqnarray|displaymath|math)\*?\}"
               r".+?\\end\{\1\*?\}", re.DOTALL),
    re.compile(r"\$\$.+?\$\$", re.DOTALL),
    re.compile(r"\\\[.+?\\\]", re.DOTALL),
    re.compile(r"\\\(.+?\\\)", re.DOTALL),
    re.compile(r"\$[^$]{1,400}?\$", re.DOTALL),
]
_CITE_TEX = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
_REF_TEX = re.compile(r"\\(?:eq|auto|c|C|page|name|v)?ref\*?\{([^}]*)\}")
_CITE_NUM = re.compile(r"\[\s*(\d+(?:\s*[-,;]\s*\d+)*)\s*\]")
_YEAR = re.compile(r"(?<![\d.,])((?:19|20)\d{2}[a-z]?)\b(?!\s?%)")
_XREF = re.compile(
    r"\b(Figs?|Figures?|Tables?|Eqs?|Eqns?|Equations?|Sections?|Secs?|Appendix|Appendices|"
    r"Chapters?)\.?\s*\(?(\d+(?:\.\d+)*[a-z]?|[A-Z](?![A-Za-z]))\)?"
    r"((?:\s*(?:,|and|&|-|to)\s*\(?\d+[a-z]?\)?(?![\d.%]))*)")
_XREF_NAMES = {"fig": "fig", "figs": "fig", "figure": "fig", "figures": "fig", "table": "table",
               "tables": "table", "eq": "eq", "eqs": "eq", "eqn": "eq", "eqns": "eq",
               "equation": "eq", "equations": "eq", "section": "section", "sections": "section",
               "sec": "section", "secs": "section", "appendix": "appendix",
               "appendices": "appendix", "chapter": "chapter", "chapters": "chapter"}
_TERM = re.compile(r"\b[A-Za-z]+(?:-[A-Za-z0-9]+)+\b")
_STRIP = ".,;:()[]{}\"'“”‘’!?"
_OPERATORS = "=<>≤≥≈±≠∝+÷→~"

_NON_NAMES = set("""In On At By During Since Until From After Before See The And For As Of To
January February March April May June July August September October November December Fig Figs
Figure Table Eq Section Chapter Appendix Ref Refs Around About Between Through Early Late Mid
Year Years Circa Version Copyright""".split())
_ELEMENTS = set("""Al Cu Si Ge Fe Ni Ti Zn Ag Au Mg Mn Cr Co Mo Sn Pb Pt Li Na Ca Cd Te Ga Se Zr
Nb Ta Hf Ar Ne Kr Xe Cl Br Ba Sr Cs Rb Sc Pd Rh Ru Ir Bi Sb Hg Tl La Ce Nd Gd Yb Er Eu Sm Dy Th
Pu""".split())

_NUMBER_WORDS = set("""two three four five six seven eight nine ten eleven twelve thirteen fourteen
fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety
hundred thousand million billion third fourth fifth sixth seventh eighth ninth tenth dozen""".split())
_POLARITY = {w: w for w in """not no never none neither nor cannot without less fewer greater
smaller larger higher lower highest lowest above below before after positive negative inlet outlet
upper inner outer hot cold half twice double triple least""".split()}
_POLARITY.update({"max": "max", "maximum": "max", "maximal": "max", "min": "min",
                  "minimum": "min", "minimal": "min", "rose": "UP", "grew": "UP", "fell": "DOWN",
                  "loss": "DOWN", "losses": "DOWN", "lowered": "DOWN", "lowers": "DOWN",
                  "lowering": "DOWN"})
_POLARITY_STEMS = [("increas", "UP"), ("rais", "UP"), ("grow", "UP"), ("gain", "UP"),
                   ("decreas", "DOWN"), ("drop", "DOWN"), ("fall", "DOWN"), ("reduc", "DOWN"),
                   ("declin", "DOWN"), ("diminish", "DOWN")]
_POLARITY_EXACT_UP = {"rise", "rises", "rising", "risen"}
_CHECK_WORDS = set("""more most over under up down high low large small first second last one both
all only long short fast slow top bottom front back left right input output single few many every
each always often new old same different main major minor total average mean peak""".split())
_FUNCTION = set("""the a an of in on at to for by with from as is are was were be been being has
have had do does did and or but if that which who whom whose this these those it its their they
them there here then than so such also can could may might will would shall should must into
onto about between through during while when where because although though however thus therefore
hence moreover furthermore additionally we our us i he she his her you your what how why very
just any some other another via due per et al""".split())


# --------------------------------------------------------------------------- normalisation

def normalise(text):
    """Fold the notations that mean the same thing so that only real changes differ."""
    text = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+", lambda m: "^" + m.group(0).translate(_SUP), text)
    text = re.sub(r"[₀₁₂₃₄₅₆₇₈₉₊₋]+", lambda m: "_" + m.group(0).translate(_SUB), text)
    text = text.replace("\u2014", ", ").replace("---", ", ")      # em dash is punctuation
    text = re.sub(r"\s\u2013\s", ", ", text)                      # spaced en dash is punctuation
    text = text.replace("\u2013", "-")                            # en dash in a range
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"\]\s*-\s*\[", "-", text)
    text = text.replace("<=", "≤").replace(">=", "≥").replace("!=", "≠").replace("+/-", "±")
    text = text.replace("\\times", "×").replace("\\pm", "±")
    text = re.sub(r"(\d)\s*percent\b", r"\1%", text)
    text = re.sub(r"(\d(?:\.\d+)?)[eE]([-+\u2212]?\d+)\b",
                  lambda m: f"{m.group(1)}×10^{m.group(2).replace(chr(0x2212), '-')}", text)
    text = re.sub(r"\s*(?:×|(?<=\d)\s?x(?=\s?10))\s*10\s*\^?\s*\{?\s*([-+\u2212]?\d+)\s*\}?",
                  lambda m: f"×10^{m.group(1).replace(chr(0x2212), '-').lstrip('+')}", text)
    text = re.sub(r"\^\{([-+]?\d+)\}", r"^\1", text)
    text = re.sub(r"\s*([=<>≤≥≈±≠∝])\s*", r" \1 ", text)
    # "41.1°C" and "5mm" read the same as "41.1 °C" and "5 mm".
    text = re.sub(r"(?<![A-Za-z_^\d.,])(\d+(?:\.\d+)?(?:×10\^[-+]?\d+)?)(?=[°A-Za-zμΩ])", r"\1 ", text)
    return text


def _mark_minus(work):
    """Turn each minus sign into a negative-number marker or a binary-operator marker."""
    def mathy(ch):
        return ch.isdigit() or ch in ")]}"

    def repl(m):
        s, i, j = m.string, m.start(), m.end()
        ch = m.group(1)
        spaced_before = i > 0 and s[i - 1].isspace()
        k = i - 1
        while k >= 0 and s[k].isspace():
            k -= 1
        prev = s[k] if k >= 0 else ""
        nxt = s[j:j + 1]
        single_letter_before = prev.isalpha() and (k == 0 or not s[k - 1].isalnum())
        if nxt.isdigit():
            if ch == "-" and not spaced_before and prev.isalnum():
                return m.group(0)                      # range or compound: 4-7, AP-110
            if mathy(prev) or single_letter_before:
                return f" {_MINUS} "                   # 5 − 3, a − 2
            return _NEG                                # to −40, (−40, = −40
        if ch == "\u2212":
            return f" {_MINUS} "                       # a − b
        if spaced_before and (mathy(prev) or single_letter_before) and \
                (nxt.isalpha() and not s[j + 1:j + 2].isalnum()):
            return f" {_MINUS} "                       # a - b
        return m.group(0)
    return re.sub(r"([-\u2212])\s?(?=\S)", repl, work)


def _norm_num(raw):
    n = re.sub(r"\s+", "", raw)
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", n):
        n = n.replace(",", "")
    return n


def _stem(word):
    if len(word) >= 6:
        for suf in ("ings", "ing", "edly", "ed", "es", "ly", "s"):
            if word.endswith(suf) and len(word) - len(suf) >= 4:
                return word[:-len(suf)]
    return word


def _content_stems(text):
    return {_stem(w) for w in re.findall(r"[^\W\d_]{2,}", text.lower()) if w not in _FUNCTION}


def _polarity_key(word):
    if word in _POLARITY:
        return _POLARITY[word]
    if word in _POLARITY_EXACT_UP:
        return "UP"
    for stem, key in _POLARITY_STEMS:
        if word.startswith(stem):
            return key
    return None


# --------------------------------------------------------------------------- extraction

def _author_year(work, out):
    """Find author-year citations; return `work` with them blanked out."""
    spans = []
    for m in _YEAR.finditer(work):
        head = work[max(0, m.start() - 90):m.start()]
        tail = head.rstrip(" \t\n,([")
        names, pos = [], len(tail)
        for tok in reversed(re.findall(r"\S+", tail)):
            start = tail.rfind(tok, 0, pos)
            bare = tok.strip(_STRIP)
            low = bare.lower()
            if low in ("and", "&", "et", "al"):
                pos = start
                continue
            if (len(bare) >= 2 and bare[0].isupper() and bare not in _NON_NAMES
                    and re.fullmatch(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", bare)):
                names.append(low)
                pos = start
                if tok.startswith(("(", "[")):
                    break
                continue
            break
        if names:
            out["citations"].update([" ".join(reversed(names)) + " " + m.group(1)])
            begin = max(0, m.start() - 90) + pos
            end = m.end()
            if work[end:end + 1] in ")]":
                end += 1
            spans.append((begin, end))
    for begin, end in reversed(spans):
        work = work[:begin] + " " * (end - begin) + work[end:]
    return work


def extract_technical(text):
    """Return {category: Counter} of the technical items in `text`."""
    out = {c: Counter() for c in CATEGORIES}
    out["_sequence"] = []
    work = normalise(text)

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
    take(_REF_TEX, lambda m: out["crossrefs"].update(
        "ref:" + k.strip() for k in m.group(1).split(",") if k.strip()))

    def cite_num(m):
        for part in re.split(r"[,;]", m.group(1)):
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

    def xref(m):
        name = _XREF_NAMES[m.group(1).lower()]
        out["crossrefs"].update([f"{name} {m.group(2).lower()}"])
        rest = m.group(3) or ""
        plural = m.group(1).lower().rstrip(".").endswith(("s", "ces"))
        if rest and plural:
            prev = m.group(2)
            for sep, num in re.findall(r"(,|and|&|-|to)\s*\(?(\d+[a-z]?)\)?", rest):
                if sep in ("-", "to") and prev.isdigit() and num.isdigit() \
                        and 0 < int(num) - int(prev) <= 50:
                    out["crossrefs"].update(f"{name} {i}" for i in range(int(prev) + 1, int(num) + 1))
                else:
                    out["crossrefs"].update([f"{name} {num.lower()}"])
                prev = num
            return " "
        return " " + rest if rest else " "
    work = _XREF.sub(xref, work)

    work = _author_year(work, out)
    work = _mark_minus(work)

    # Operators and comparators.
    for ch in _OPERATORS:
        n = work.count(ch)
        if n:
            out["operators"][ch] += n
    n = work.count(_MINUS)
    if n:
        out["operators"]["minus"] += n
    n = len(re.findall(r"×(?!10\^)", work))
    if n:
        out["operators"]["×"] += n

    # Numbers and quantities.
    for m in _NUM.finditer(work):
        start, end = m.span()
        before = work[start - 1] if start else " "
        if before.isalpha() or before in "_^":
            continue  # part of a symbol such as CO2, x_1, x^2
        num = _norm_num(m.group(0))
        if before == _NEG:
            num = "-" + num
        unit = _UNIT.match(work, end)
        u = ""
        if unit and unit.group(1).strip():
            u = re.sub(r"\s+", " ", unit.group(1).strip())
            u = re.sub(r"\s?([/·])\s?", r"\1", u)
        elif work[end:end + 1] not in ".,;:!?)]":
            nb = re.match(r"\s?(\S+)", work[end:])
            if nb:
                tok = nb.group(1).rstrip(_STRIP)
                if (tok and not tok[0].isdigit() and tok[0] not in "([<>=≤≥≈±×+" + _NEG + _MINUS
                        and tok.lower() not in _FUNCTION
                        and not (tok.isalpha() and (len(tok) > 6 or tok.lower() in _CHECK_WORDS
                                                    or _polarity_key(tok.lower())))):
                    u = tok
        if u:
            out["quantities"].update([f"{num} {u}"])
            if u == "%":
                num += "%"
        out["numbers"].update([num])
        out["_sequence"].append(num)

    for tok in work.split():
        tok = tok.strip(_STRIP + _NEG + _MINUS)
        if tok.endswith("'s") or tok.endswith("’s"):
            tok = tok[:-2]
        if not tok or not any(c.isalpha() for c in tok):
            continue
        if len(tok) == 1:
            if tok not in ("a", "A", "I"):
                out["symbols"].update([tok])
            continue
        if (any(c.isupper() for c in tok[1:]) or any(c.isdigit() for c in tok)
                or any(c.isalpha() and ord(c) > 0x036F for c in tok)
                or "_" in tok or "^" in tok or tok in _ELEMENTS):
            out["symbols"].update([tok])

    out["terms"].update(t.lower() for t in _TERM.findall(work))

    for w in re.findall(r"[a-z]+(?:n't)?", work.lower()):
        if w.endswith("n't"):
            out["polarity"].update(["not"])
            continue
        if w in _NUMBER_WORDS:
            out["number_words"].update([w])
        key = _polarity_key(w)
        if key:
            out["polarity"].update([key])
    out["_check_words"] = Counter(
        w for w in re.findall(r"[a-z]+", work.lower()) if w in _CHECK_WORDS)
    out["_work"] = work
    return out


# --------------------------------------------------------------------------- comparison

def _fmt(counter):
    return ", ".join(f"{k}" + (f" x{v}" if v > 1 else "") for k, v in sorted(counter.items()))


def compare(original, rewrite, protect=None, accept=None, strict=False):
    """Return (ok, report). ok is False when a technical item was lost, changed, or added."""
    a, b = extract_technical(original), extract_technical(rewrite)
    accept = {w.strip().lower() for w in (accept or []) if w.strip()}
    lines, fails, checks = [], 0, 0

    for cat in CATEGORIES:
        missing, added = a[cat] - b[cat], b[cat] - a[cat]
        soft = Counter()
        if cat in PRESENCE:
            for k in set(missing) | set(added):
                if k in a[cat] and k in b[cat]:
                    soft[k] = 1
            if cat == "terms":
                low_a, low_b = a["_work"].lower(), b["_work"].lower()
                for k in list(missing):
                    if k not in soft and re.search(k.replace("-", r"[\s-]?"), low_b):
                        soft[k] = 1
                for k in list(added):
                    if k not in soft and re.search(k.replace("-", r"[\s-]?"), low_a):
                        soft[k] = 1
            missing = Counter({k: v for k, v in missing.items() if k not in soft})
            added = Counter({k: v for k, v in added.items() if k not in soft})
        if cat == "polarity" and accept:
            waived = {k for k in set(missing) | set(added) if k.lower() in accept}
            if waived:
                lines.append("ACCEPTED polarity change (name each in the report): " + ", ".join(
                    f"{k} ({a[cat][k]} -> {b[cat][k]})" for k in sorted(waived)))
            missing = Counter({k: v for k, v in missing.items() if k not in waived})
            added = Counter({k: v for k, v in added.items() if k not in waived})
        if missing or added:
            fails += 1
            lines.append(f"FAIL {cat}:")
            if missing:
                lines.append("    missing from rewrite: " + _fmt(missing))
            if added:
                lines.append("    added in rewrite: " + _fmt(added))
        else:
            lines.append(f"ok   {cat}: {sum(a[cat].values())} items match")
        if soft:
            checks += 1
            lines.append(f"CHECK {cat}, mention count or hyphenation changed: " + ", ".join(
                f"{k} ({a[cat][k]} -> {b[cat][k]})" for k in sorted(soft)))

    if a["numbers"] == b["numbers"] and a["_sequence"] != b["_sequence"]:
        checks += 1
        lines.append("CHECK numbers appear in a different order. Confirm each number still belongs "
                     "to the same quantity:")
        lines.append("    original: " + " ".join(a["_sequence"]))
        lines.append("    rewrite:  " + " ".join(b["_sequence"]))

    cw_a, cw_b = a["_check_words"], b["_check_words"]
    changed = sorted(k for k in set(cw_a) | set(cw_b) if cw_a[k] != cw_b[k])
    if changed:
        checks += 1
        lines.append("CHECK quantity and direction words changed count (confirm no meaning "
                     "changed): " + ", ".join(f"{k} ({cw_a[k]} -> {cw_b[k]})" for k in changed))

    for phrase in protect or []:
        pat = re.compile(r"\s+".join(re.escape(w) for w in phrase.split()), re.IGNORECASE)
        na, nb = len(pat.findall(original)), len(pat.findall(rewrite))
        if na and not nb:
            fails += 1
            lines.append(f"FAIL protected phrase missing from rewrite: {phrase}")
        elif na != nb:
            checks += 1
            lines.append(f"CHECK protected phrase count changed: {phrase} ({na} -> {nb})")
        elif not na:
            lines.append(f"note: protected phrase does not occur in the original: {phrase}")

    sa, sb = _content_stems(a["_work"]), _content_stems(b["_work"])
    gone, new = sorted(sa - sb), sorted(sb - sa)
    if gone:
        lines.append("REVIEW words removed (confirm none is a technical term): " + ", ".join(gone))
    if new:
        lines.append("REVIEW words added (confirm none adds a claim): " + ", ".join(new))
    if not sum(sum(a[c].values()) for c in CATEGORIES):
        lines.append("note: no technical items were found in the original.")

    ok = fails == 0 and not (strict and checks)
    if fails or (strict and checks):
        head = "FAIL: technical content changed. Repair or discard the rewrite."
    elif checks:
        head = (f"PASS, with {checks} CHECK item(s) to confirm by reading. Name each in the report.")
    else:
        head = "PASS: every compared technical item is intact."
    return ok, "\n".join([head] + lines)


def _read(path):
    if path.lower().endswith((".pdf", ".docx")):
        return extract_text(path)
    return read_text(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("rewrite")
    ap.add_argument("--protect", help="text file of phrases (one per line) that must survive")
    ap.add_argument("--accept", default="",
                    help="comma-separated polarity words whose count change is deliberate")
    ap.add_argument("--strict", action="store_true", help="treat every CHECK as a FAIL")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for p in (args.original, args.rewrite, args.protect):
        if p and not os.path.isfile(p):
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2
    try:
        original, rewrite = _read(args.original), _read(args.rewrite)
    except Exception as exc:
        print(f"error: could not read input: {exc}", file=sys.stderr)
        return 2
    if not original.strip() or not rewrite.strip():
        print("error: the original or the rewrite contains no text; nothing was compared.",
              file=sys.stderr)
        return 2
    protect = None
    if args.protect:
        protect = [line.strip() for line in read_text(args.protect).splitlines() if line.strip()]
    ok, report = compare(original, rewrite, protect, args.accept.split(","), args.strict)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
