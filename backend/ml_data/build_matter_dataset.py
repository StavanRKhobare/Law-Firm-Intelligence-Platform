"""
Build the matter-type training set from Supreme Court of India judgments.

Source: balamurugan205799/Indian-Supreme-Court-Judgments on Hugging Face (CC BY 4.0),
English PDFs for 2018 and 2020 (~1,350 judgments). Text is the first 4 pages
(headnote plus the start of the judgment), extracted with pypdf into a JSONL file
of {"file", "text"} rows.

Labels are weak labels: each judgment is scored against keyword/statute lists
for five matter types and gets the highest-scoring one. Nobody hand-labelled
these rows. The case-number line ("Civil Appeal No...", "Criminal Appeal...")
is used as a tie-breaker and then removed from the text so the model cannot
read the answer off it.

Usage:
    python ml_data/build_matter_dataset.py judgments.jsonl ml_data/matter_types.csv
"""

import csv
import json
import re
import sys

LABELS = ["Criminal", "Civil", "Family", "Corporate", "Constitutional"]

# (pattern, weight). Statute names weigh more than common words.
KEYWORDS = {
    "Criminal": [
        (r"penal code|\bI\.?P\.?C\b|bharatiya nyaya sanhita", 3),
        (r"code of criminal procedure|cr\.?\s?p\.?c", 3),
        (r"\bNDPS\b|narcotic|prevention of corruption act|arms act", 3),
        (r"\baccused\b|conviction|convicted|acquittal|acquitted", 1),
        (r"\bbail\b|murder|prosecution|charge-?sheet|\bFIR\b|sentence", 1),
    ],
    "Family": [
        (r"hindu marriage act|special marriage act|family courts? act", 4),
        (r"hindu succession act|hindu adoptions|guardians and wards act", 4),
        (r"divorce|matrimonial|custody of the (child|minor)|dowry", 2),
        (r"\bwife\b|\bhusband\b|marriage|alimony", 1),
    ],
    "Corporate": [
        (r"companies act|insolvency and bankruptcy|\bIBC\b|corporate debtor", 4),
        (r"arbitration and conciliation act|\bSEBI\b|competition act", 3),
        (r"income[- ]tax act|central excise|customs act|\bGST\b|finance act", 3),
        (r"shareholder|debenture|\barbitra(l|tor|tion)\b|assessee|\bbank\b", 1),
    ],
    "Constitutional": [
        (r"article (14|16|19|21|32|226|136|311)\b", 2),
        (r"fundamental rights?|writ petition|constitution of india", 2),
        (r"service law|seniority|promotion|recruitment rules|pay scale", 2),
        (r"public interest litigation|ultra vires|reservation", 2),
    ],
    "Civil": [
        (r"code of civil procedure|\bC\.?P\.?C\b|specific relief act", 3),
        (r"land acquisition|transfer of property act|limitation act|motor vehicles act", 3),
        (r"\bsuit\b|decree|plaintiff|defendant|landlord|tenant|sale deed", 1),
        (r"possession|easement|partition|compensation", 1),
    ],
}

CASE_LINE = re.compile(
    r"\((civil|criminal)\s+appeal[^)]*\)|\(writ\s+petition[^)]*\)|\((transfer|special leave|review)\s+petition[^)]*\)",
    re.I,
)
COMPILED = {k: [(re.compile(p, re.I), w) for p, w in v] for k, v in KEYWORDS.items()}


def score(text):
    return {lab: sum(w * len(p.findall(text)) for p, w in pats) for lab, pats in COMPILED.items()}


def label(text):
    s = score(text)
    m = CASE_LINE.search(text)
    kind = m.group(0).lower() if m else ""
    # Tie-breaker / prior from the case-number line.
    if "criminal" in kind:
        s["Criminal"] += 3
    elif "writ" in kind:
        s["Constitutional"] += 3
    elif "civil" in kind:
        s["Civil"] += 2
    best = max(LABELS, key=lambda k: s[k])
    return best if s[best] >= 4 else None


def clean(text):
    text = CASE_LINE.sub(" ", text)
    text = re.sub(r"^[A-H]\s*$", " ", text, flags=re.M)  # SCR margin letters
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:6000]


def main(src, dst):
    rows, skipped = [], 0
    with open(src) as f:
        for line in f:
            d = json.loads(line)
            lab = label(d["text"])
            if lab is None:
                skipped += 1
                continue
            rows.append({"source_file": d["file"], "matter_type": lab, "text": clean(d["text"])})
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source_file", "matter_type", "text"])
        w.writeheader()
        w.writerows(rows)
    counts = {k: sum(r["matter_type"] == k for r in rows) for k in LABELS}
    print(f"wrote {len(rows)} rows to {dst} (skipped {skipped} with no clear signal)")
    print(counts)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
