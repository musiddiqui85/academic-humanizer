"""Shared text extraction, cleaning, and statistical metrics for the academic-humanizer skill.

Standard library only. PDF extraction calls the `pdftotext` command-line tool.
"""
import os
import re
import statistics
import subprocess
import zipfile

CONNECTIVES = [
    "however", "moreover", "furthermore", "additionally", "therefore", "thus", "hence",
    "consequently", "notably", "importantly", "overall", "specifically", "in addition",
    "in particular", "in contrast", "on the other hand",
]

SUPPORTED = (".pdf", ".docx", ".tex", ".txt", ".md")

_PLACEHOLDER = "\x00"
_ABBR = re.compile(
    r"\b(?:et al|e\.g|i\.e|Fig|Figs|Eq|Eqs|Ref|Refs|vs|cf|approx|No|Sec|Tab|resp|ca|Dr|Prof|"
    r"Mr|Ms|Inc|Ltd|Co|Vol|pp|wt|vol|viz)\.",
    re.IGNORECASE,
)
_INITIAL_CHAIN = re.compile(r"\b([A-Z])\.(?=\s?[A-Z]\.)")
_INITIAL_NAME = re.compile(r"(?<!\d\s)(?<!°)\b([A-Z])\.(?=\s+[A-Z][a-z])")
_SPLIT = re.compile(r"([.!?][\"”')\]]*)\s+(?=[\"“(\[]?[A-Z])")
_CITATION = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
_WORD = re.compile(r"[A-Za-z0-9]+(?:[-'’/.][A-Za-z0-9]+)*")
_ALPHA_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
_HEADING_CUT = re.compile(
    r"^\s*(?:\d+\.?\s*)?(?:references|bibliography|acknowledge?ments?|literature cited)\s*:?\s*$",
    re.IGNORECASE,
)
_INTRO = re.compile(r"^\s*(?:1\.?\s+|I\.\s+)?introduction\s*$", re.IGNORECASE)
_CAPTION = re.compile(r"^\s*(?:Fig|Figs|Figure|Table|Scheme|Chart)\.?\s*\d+[a-z]?[.:]?\s+[A-Z(]")
_TERMINAL = re.compile(r"[.!?:;][\"”')\]]*$")


# --------------------------------------------------------------------------- extraction

def _pdf_text(path):
    try:
        out = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", path, "-"],
            capture_output=True, check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext is not installed or not on PATH") from exc
    return out.stdout.decode("utf-8", errors="replace")


def _docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.DOTALL):
        runs = re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.DOTALL)
        text = "".join(runs)
        text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&apos;", "'"))
        if text.strip():
            paras.append(text)
    return "\n\n".join(paras)


def _tex_text(src):
    src = re.sub(r"(?<!\\)%.*", "", src)
    m = re.search(r"\\begin\{document\}", src)
    if m:
        src = src[m.end():]
    src = re.sub(
        r"\\begin\{(equation|align|gather|multline|eqnarray|table|figure|tabular|thebibliography)"
        r"\*?\}.*?\\end\{\1\*?\}", " ", src, flags=re.DOTALL)
    src = re.sub(r"\$\$.*?\$\$|\\\[.*?\\\]", " ", src, flags=re.DOTALL)
    src = re.sub(r"\$[^$]*\$|\\\(.*?\\\)", "x", src, flags=re.DOTALL)
    src = re.sub(r"~?\\(?:cite[tp]?|citep|citet|citeauthor|citeyear)\*?(?:\[[^\]]*\])*\{[^}]*\}", " [1]", src)
    src = re.sub(r"~?\\(?:ref|eqref|autoref|cref|Cref)\{[^}]*\}", " 1", src)
    src = re.sub(r"\\(?:label|bibliography|bibliographystyle|input|include|vspace|hspace)\{[^}]*\}", " ", src)
    src = re.sub(r"\\(?:section|subsection|subsubsection|paragraph|title|author|date)\*?\{[^}]*\}", "\n\n", src)
    src = re.sub(r"\\(?:begin|end)\{[^}]*\}", "\n\n", src)
    src = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", src)
    src = re.sub(r"\\[a-zA-Z]+\*?", " ", src)
    src = src.replace("{", "").replace("}", "").replace("~", " ").replace("\\", " ")
    return src


def extract_text(path):
    """Return the raw text of a .pdf, .docx, .tex, .txt, or .md file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _pdf_text(path)
    if ext == ".docx":
        return _docx_text(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if ext == ".tex":
        return _tex_text(src)
    return src


# --------------------------------------------------------------------------- cleaning

def _letter_ratio(s):
    if not s:
        return 0.0
    good = sum(1 for c in s if c.isalpha() or c.isspace())
    return good / len(s)


def count_words(s):
    return len(_WORD.findall(_CITATION.sub(" ", s)))


def clean_body(text, line_paragraphs=False, min_words=40, filter_lines=True, start_at_intro=False):
    """Return the paragraphs of body prose in `text`.

    line_paragraphs: each line is one paragraph (pdftotext output). Otherwise paragraphs are
        separated by blank lines and single newlines are soft wraps.
    min_words: drop shorter paragraphs. filter_lines: drop captions, equation and table lines.
    start_at_intro: discard everything before an "Introduction" heading when one exists.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    lines = text.split("\n")

    for i, line in enumerate(lines):
        if _HEADING_CUT.match(line):
            # Keep the cut only if it falls in the back half, or there is nothing after it anyway.
            if i > len(lines) * 0.3 or not line_paragraphs:
                lines = lines[:i]
                break
    if start_at_intro:
        for i, line in enumerate(lines):
            if _INTRO.match(line) and i < len(lines) * 0.5:
                lines = lines[i + 1:]
                break

    if filter_lines:
        ratio_floor = 0.75 if line_paragraphs else 0.6
        kept = []
        for line in lines:
            s = line.strip()
            if s and (_CAPTION.match(s) or _letter_ratio(s) < ratio_floor):
                continue
            kept.append(line)
        lines = kept

    if line_paragraphs:
        blocks = [l.strip() for l in lines if l.strip()]
    else:
        joined = "\n".join(lines)
        joined = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", joined)
        blocks = [re.sub(r"\s*\n\s*", " ", b).strip() for b in re.split(r"\n\s*\n", joined)]
        blocks = [b for b in blocks if b]

    # Re-join paragraphs broken by a page or column break.
    merged = []
    pending = None
    for b in blocks:
        if pending is not None and b[0].islower():
            prev = merged[pending]
            if re.search(r"[A-Za-z]-$", prev):
                merged[pending] = prev[:-1] + b
            else:
                merged[pending] = prev + " " + b
            if _TERMINAL.search(merged[pending]):
                pending = None
            continue
        merged.append(b)
        if not _TERMINAL.search(b) and count_words(b) >= 20:
            pending = len(merged) - 1

    out = []
    for b in merged:
        b = re.sub(r"\s+", " ", b).strip()
        if count_words(b) < max(min_words, 1):
            continue
        if filter_lines and (not re.search(r"[.!?]", b) or _letter_ratio(b) < 0.8):
            continue
        out.append(b)
    return out


def load_paragraphs(path, raw=False):
    """Extract and clean a file. raw=True keeps every paragraph (for pasted drafts)."""
    text = extract_text(path)
    is_pdf = path.lower().endswith(".pdf")
    if raw and not is_pdf:
        return clean_body(text, min_words=0, filter_lines=False)
    return clean_body(text, line_paragraphs=is_pdf, start_at_intro=is_pdf,
                      min_words=0 if raw else 40)


# --------------------------------------------------------------------------- sentences

def split_sentences(paragraph):
    s = _ABBR.sub(lambda m: m.group(0)[:-1] + _PLACEHOLDER, paragraph)
    prev = None
    while prev != s:
        prev = s
        s = _INITIAL_CHAIN.sub(lambda m: m.group(1) + _PLACEHOLDER, s)
    s = re.sub(r"(?<=" + _PLACEHOLDER + r")(\s?[A-Z])\.(?=\s+[A-Z][a-z])",
               lambda m: m.group(1) + _PLACEHOLDER, s)
    s = _INITIAL_NAME.sub(lambda m: m.group(1) + _PLACEHOLDER, s)
    parts = _SPLIT.split(s)
    sentences = []
    for i in range(0, len(parts), 2):
        sent = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
        sent = sent.replace(_PLACEHOLDER, ".").strip()
        if count_words(sent) >= 3:
            sentences.append(sent)
    return sentences


# --------------------------------------------------------------------------- metrics

def _cv(values):
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    return statistics.pstdev(values) / mean if mean else 0.0


def _mattr(words, window=100):
    if not words:
        return 0.0
    if len(words) <= window:
        return len(set(words)) / len(words)
    counts = {}
    for w in words[:window]:
        counts[w] = counts.get(w, 0) + 1
    total = len(counts)
    n = 1
    for i in range(window, len(words)):
        old = words[i - window]
        counts[old] -= 1
        if counts[old] == 0:
            del counts[old]
        new = words[i]
        counts[new] = counts.get(new, 0) + 1
        total += len(counts)
        n += 1
    return total / n / window


def _conn_key(c):
    return "conn_" + c.replace(" ", "_") + "_per_1000"


BASE_KEYS = [
    "sent_len_mean", "sent_len_sd", "sent_len_cv", "short_share", "long_share",
    "adjacent_diff_mean", "para_len_cv", "opener_repeat_rate", "initial_connective_share",
    "connective_per_1000", "comma_per_1000", "semicolon_per_1000", "colon_per_1000",
    "paren_per_1000", "mattr",
]
CONN_KEYS = [_conn_key(c) for c in CONNECTIVES]
METRIC_KEYS = BASE_KEYS + CONN_KEYS


def compute_metrics(paragraphs):
    """Return the statistical shape of a list of paragraphs as a flat dict of floats."""
    per_para = [split_sentences(p) for p in paragraphs]
    per_para = [s for s in per_para if s]
    sentences = [s for para in per_para for s in para]
    lengths = [count_words(s) for s in sentences]
    text = " ".join(sentences)
    n_words = sum(lengths)
    n_sent = len(sentences)
    per_k = (1000.0 / n_words) if n_words else 0.0

    m = {"n_sentences": n_sent, "n_words": n_words}
    m["sent_len_mean"] = statistics.fmean(lengths) if lengths else 0.0
    m["sent_len_sd"] = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    m["sent_len_cv"] = _cv(lengths)
    m["short_share"] = sum(1 for n in lengths if n <= 10) / n_sent if n_sent else 0.0
    m["long_share"] = sum(1 for n in lengths if n >= 35) / n_sent if n_sent else 0.0

    diffs, repeats, pairs, initial_conn = [], 0, 0, 0
    for para in per_para:
        plens = [count_words(s) for s in para]
        firsts = []
        for s in para:
            w = _ALPHA_WORD.search(s.lower())
            firsts.append(w.group(0) if w else "")
            low = s.lower().lstrip("\"“(")
            if any(re.match(re.escape(c) + r"\b", low) for c in CONNECTIVES):
                initial_conn += 1
        for a, b in zip(plens, plens[1:]):
            diffs.append(abs(a - b))
        for a, b in zip(firsts, firsts[1:]):
            pairs += 1
            if a and a == b:
                repeats += 1
    m["adjacent_diff_mean"] = statistics.fmean(diffs) if diffs else 0.0
    m["para_len_cv"] = _cv([len(p) for p in per_para])
    m["opener_repeat_rate"] = repeats / pairs if pairs else 0.0
    m["initial_connective_share"] = initial_conn / n_sent if n_sent else 0.0

    low = text.lower()
    total_conn = 0
    for c in CONNECTIVES:
        n = len(re.findall(r"\b" + re.escape(c) + r"\b", low))
        total_conn += n
        m[_conn_key(c)] = n * per_k
    m["connective_per_1000"] = total_conn * per_k

    no_cite = _CITATION.sub(" ", text)
    m["comma_per_1000"] = no_cite.count(",") * per_k
    m["semicolon_per_1000"] = no_cite.count(";") * per_k
    m["colon_per_1000"] = len(re.findall(r":(?=\s)", no_cite)) * per_k
    m["paren_per_1000"] = no_cite.count("(") * per_k
    m["mattr"] = _mattr(_ALPHA_WORD.findall(low))
    return m
