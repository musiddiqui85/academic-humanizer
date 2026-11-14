"""Build the author's statistical writing profile from a folder of their own papers.

Usage: python build_profile.py <folder> [--max-year 2022] [--out author_profile.json]
"""
import argparse
import datetime
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import METRIC_KEYS, SUPPORTED, compute_metrics, load_paragraphs  # noqa: E402

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "author_profile.json")
MIN_SENTENCES = 50


def file_year(name):
    years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", name)
    return int(years[-1]) if years else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder")
    ap.add_argument("--max-year", type=int, default=2022,
                    help="use only papers dated this year or earlier (default 2022)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not os.path.isdir(args.folder):
        print(f"error: not a folder: {args.folder}", file=sys.stderr)
        return 2

    papers, skipped, held_out, rows = [], [], [], []
    for name in sorted(os.listdir(args.folder)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in SUPPORTED or stem.endswith("_compressed"):
            continue
        year = file_year(stem)
        if year is None:
            skipped.append({"file": name, "reason": "no year in filename"})
            print(f"warning: skipped {name}: no year in filename", file=sys.stderr)
            continue
        if year > args.max_year:
            held_out.append(name)
            continue
        try:
            metrics = compute_metrics(load_paragraphs(os.path.join(args.folder, name)))
        except Exception as exc:  # a broken file must not stop the build
            skipped.append({"file": name, "reason": f"could not read: {exc}"})
            print(f"warning: skipped {name}: could not read ({exc})", file=sys.stderr)
            continue
        if metrics["n_sentences"] < MIN_SENTENCES:
            skipped.append({"file": name, "reason": "too little text"})
            print(f"warning: skipped {name}: too little text "
                  f"({metrics['n_sentences']} sentences; scanned PDF?)", file=sys.stderr)
            continue
        papers.append({"file": name, "year": year, "n_sentences": metrics["n_sentences"],
                       "n_words": metrics["n_words"]})
        rows.append(metrics)

    if not rows:
        print("error: no usable papers found", file=sys.stderr)
        return 1

    summary = {}
    for key in METRIC_KEYS:
        vals = [r[key] for r in rows]
        summary[key] = {
            "mean": statistics.fmean(vals),
            "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "min": min(vals),
            "max": max(vals),
        }

    profile = {
        "built": datetime.date.today().isoformat(),
        "max_year": args.max_year,
        "papers": papers,
        "skipped": skipped,
        "held_out": held_out,
        "metrics": summary,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    print(f"Profile built from {len(papers)} papers "
          f"({sum(p['n_sentences'] for p in papers)} sentences) -> {args.out}")
    if skipped:
        print(f"Skipped {len(skipped)}: " + "; ".join(f"{s['file']} ({s['reason']})" for s in skipped))
    if held_out:
        print(f"Left out (after {args.max_year}): " + ", ".join(held_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
