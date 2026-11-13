"""Agreement between annotators, and between humans and the automated audit.

Usage:
  python agreement.py results/annotation_A.csv results/annotation_B.csv

Each file is a filled copy of results/annotation_sheet.csv. Reports Cohen's
kappa on defect_present for annotator A vs B, and for each annotator vs the
automated label (course_fail / adversarial_only = yes, no_observed_defect = no).
"""
import csv
import sys
from collections import Counter


def kappa(a, b):
    assert len(a) == len(b) and a
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def read(path):
    with open(path) as fh:
        return {r["id"]: r["defect_present(yes/no/unsure)"].strip().lower()
                for r in csv.DictReader(fh) if r["defect_present(yes/no/unsure)"].strip()}


def automated():
    with open("results/audit.csv") as fh:
        m = {"course_fail": "yes", "adversarial_only": "yes", "no_observed_defect": "no"}
        return {r["id"]: m[r["observed"]] for r in csv.DictReader(fh) if r["observed"] in m}


if __name__ == "__main__":
    A, B = read(sys.argv[1]), read(sys.argv[2])
    auto = automated()
    ids = sorted(set(A) & set(B))
    print(f"items labelled by both annotators: {len(ids)}")
    print(f"kappa A vs B: {kappa([A[i] for i in ids], [B[i] for i in ids]):.2f}")
    for name, H in (("A", A), ("B", B)):
        j = sorted(set(H) & set(auto))
        print(f"kappa {name} vs automated: {kappa([H[i] for i in j], [auto[i] for i in j]):.2f}  (n={len(j)})")
