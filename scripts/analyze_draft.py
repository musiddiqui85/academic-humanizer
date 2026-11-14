"""Compare a draft's statistical shape with the author's profile and suggest rewrite moves.

Usage: python analyze_draft.py <draft> [--profile author_profile.json] [--json] [--raw] [--z 1.5]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textstats import BASE_KEYS, CONN_KEYS, compute_metrics, load_paragraphs  # noqa: E402

DEFAULT_PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "author_profile.json")
MIN_SENTENCES = 8

LABELS = {
    "sent_len_mean": "sentence length, mean (words)",
    "sent_len_sd": "sentence length, spread (SD)",
    "sent_len_cv": "sentence length, relative spread",
    "short_share": "share of short sentences (<=10 words)",
    "long_share": "share of long sentences (>=35 words)",
    "adjacent_diff_mean": "length change between neighbours",
    "para_len_cv": "paragraph length, relative spread",
    "opener_repeat_rate": "neighbours starting with same word",
    "initial_connective_share": "sentences opening with a connective",
    "connective_per_1000": "connectives per 1000 words",
    "comma_per_1000": "commas per 1000 words",
    "semicolon_per_1000": "semicolons per 1000 words",
    "colon_per_1000": "colons per 1000 words",
    "paren_per_1000": "parentheses per 1000 words",
    "mattr": "vocabulary spread (MATTR)",
}
PUNCT = {"comma_per_1000": "commas", "semicolon_per_1000": "semicolons",
         "colon_per_1000": "colons", "paren_per_1000": "parentheses"}


def conn_word(key):
    return key[len("conn_"):-len("_per_1000")].replace("_", " ")


def flag_metrics(draft, profile, z):
    flags = {}
    n_words = draft.get("n_words", 0)
    for key, ref in profile["metrics"].items():
        if key not in draft or ref["sd"] <= 0:
            continue
        v = draft[key]
        if key in CONN_KEYS:
            # Only overuse matters, and only when it occurs at least twice in the draft.
            if v > ref["mean"] + z * ref["sd"] and v * n_words / 1000.0 >= 1.5:
                flags[key] = "HIGH"
            continue
        if v < ref["mean"] - z * ref["sd"]:
            flags[key] = "LOW"
        elif v > ref["mean"] + z * ref["sd"]:
            flags[key] = "HIGH"
    return flags


def suggestions(draft, profile, flags):
    ref = profile["metrics"]
    out = []
    if flags.get("sent_len_cv") == "LOW" or flags.get("adjacent_diff_mean") == "LOW" \
            or flags.get("sent_len_sd") == "LOW":
        out.append("Sentence lengths are too even. Split some long sentences and merge some "
                   "short neighbours.")
    if flags.get("sent_len_cv") == "HIGH" or flags.get("sent_len_sd") == "HIGH":
        out.append("Sentence lengths swing more than the author's. Even out the extremes.")
    if flags.get("sent_len_mean") == "LOW":
        out.append(f"Sentences are shorter on average ({draft['sent_len_mean']:.1f} words vs the "
                   f"author's {ref['sent_len_mean']['mean']:.1f}). Merge related short sentences.")
    if flags.get("sent_len_mean") == "HIGH":
        out.append(f"Sentences are longer on average ({draft['sent_len_mean']:.1f} words vs the "
                   f"author's {ref['sent_len_mean']['mean']:.1f}). Split the longest ones.")
    if flags.get("short_share") == "LOW":
        out.append("Too few short sentences. State some results in under 10 words.")
    if flags.get("short_share") == "HIGH":
        out.append("Too many short sentences. Join some to the sentence they qualify.")
    if flags.get("long_share") == "LOW":
        out.append("Too few long sentences. Let a few explanations run long, as the author does.")
    if flags.get("long_share") == "HIGH":
        out.append("Too many very long sentences. Split a few at a natural clause boundary.")
    if flags.get("para_len_cv") == "LOW":
        out.append("Paragraphs are near-equal. Let them follow the content: some two sentences, "
                   "some eight.")
    if flags.get("opener_repeat_rate") == "HIGH":
        out.append("Neighbouring sentences start the same way. Vary the openers.")
    if flags.get("initial_connective_share") == "HIGH":
        out.append("Too many sentences open with a connective (However, Moreover, ...). "
                   "Move it inside the sentence or cut it.")
    conn_hits = [k for k in CONN_KEYS if flags.get(k) == "HIGH"]
    for k in conn_hits:
        out.append(f"Connective overused: '{conn_word(k)}' at {draft[k]:.1f} per 1000 words vs "
                   f"the author's {ref[k]['mean']:.1f}. Cut or let the logic carry.")
    if flags.get("connective_per_1000") == "HIGH" and not conn_hits:
        out.append(f"Connectives overall are high ({draft['connective_per_1000']:.1f} per 1000 vs "
                   f"the author's {ref['connective_per_1000']['mean']:.1f}). Cut the ones that "
                   "add no logic.")
    for k, name in PUNCT.items():
        if k in flags:
            more = "more" if flags[k] == "HIGH" else "less"
            out.append(f"Uses {name} {more} than the author ({draft[k]:.1f} vs "
                       f"{ref[k]['mean']:.1f} per 1000 words).")
    if flags.get("mattr") == "HIGH":
        out.append("Vocabulary is more varied than the author's. Repeat the technical term "
                   "instead of cycling synonyms.")
    if flags.get("mattr") == "LOW":
        out.append("Vocabulary is less varied than the author's. Reduce repeated filler words.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("draft")
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    ap.add_argument("--json", action="store_true", help="print machine-readable output")
    ap.add_argument("--raw", action="store_true",
                    help="keep every paragraph (use for drafts pasted as plain text)")
    ap.add_argument("--z", type=float, default=1.5,
                    help="flag a metric outside the author's mean +/- z SD (default 1.5)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not os.path.isfile(args.profile):
        print(f"error: no author profile at {args.profile}. Build one first:\n"
              f"  python build_profile.py <folder of the author's own papers>", file=sys.stderr)
        return 2
    if not os.path.isfile(args.draft):
        print(f"error: draft not found: {args.draft}", file=sys.stderr)
        return 2
    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)

    draft = compute_metrics(load_paragraphs(args.draft, raw=args.raw))
    n = draft["n_sentences"]
    if n < MIN_SENTENCES:
        msg = f"Too short to judge ({n} sentences); statistics need at least {MIN_SENTENCES}."
        if args.json:
            print(json.dumps({"too_short": True, "n_sentences": n, "message": msg,
                              "metrics": draft, "flags": {}, "suggestions": []}))
        else:
            print(msg)
        return 0

    flags = flag_metrics(draft, profile, args.z)
    moves = suggestions(draft, profile, flags)
    if args.json:
        print(json.dumps({"too_short": False, "n_sentences": n, "n_words": draft["n_words"],
                          "metrics": draft, "flags": flags, "suggestions": moves}, indent=2))
        return 0

    ref = profile["metrics"]
    print(f"Draft: {n} sentences, {draft['n_words']} words. "
          f"Author profile: {len(profile.get('papers', []))} papers.")
    print(f"{'metric':<40}{'draft':>8}{'author':>9}{'author range':>18}  flag")
    rows = [k for k in BASE_KEYS if k in ref] + [k for k in CONN_KEYS if k in flags]
    for k in rows:
        r = ref[k]
        lo, hi = max(0.0, r["mean"] - args.z * r["sd"]), r["mean"] + args.z * r["sd"]
        label = LABELS.get(k, f"'{conn_word(k)}' per 1000 words")
        print(f"{label:<40}{draft[k]:>8.2f}{r['mean']:>9.2f}{f'{lo:.2f} to {hi:.2f}':>18}  "
              f"[{k}] {flags.get(k, '')}".rstrip())
    print()
    if moves:
        print("Suggested moves:")
        for m in moves:
            print(f"  - {m}")
    else:
        print("No flags: the draft's statistical shape is within the author's range.")
    if draft["n_words"] < 300:
        print("\nNote: under 300 words the statistics are noisy. Treat flags as hints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
