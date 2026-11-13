"""Flaw-validity audit for Navigator-style code.

For every candidate (deterministic mutants, plus any LLM-generated code you add
under candidates/), the audit records two things separately:

  intended_flaw   what the generator says it did (known for mutants,
                  only *claimed* for LLM output)
  observed        what the code actually does under testing:
                    load_error          does not even run
                    course_fail         fails the lab-style tests
                    adversarial_only    passes lab tests, fails edge/random
                                        differential tests (the subtle ones)
                    no_observed_defect  passes everything we ran; either
                                        equivalent to the reference or beyond
                                        our tests, so it goes to human review

Nothing is filtered out. Subtle and unobserved cases are kept, because they
are exactly the ones a student is least likely to catch.

Usage:  python audit.py            # writes results/audit.csv and results/report.md
"""
import csv
import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT_S = 10


def _worker():
    sys.path.insert(0, HERE)
    import problems as P
    job = json.loads(sys.stdin.read())
    prob = P.PROBLEMS[job["problem"]]
    ns = {"ListNode": P.ListNode, "TreeNode": P.TreeNode, "float": float}
    try:
        exec(compile(job["code"], "<candidate>", "exec"), ns)
        f = ns[prob["entry"]]
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"load_error": f"{type(e).__name__}: {e}"}))
        return
    outs = []
    for args in job["inputs"]:
        try:
            outs.append(repr(prob["run"](f, tuple(args))))
        except RecursionError:
            outs.append("EXC:RecursionError")
        except Exception as e:  # noqa: BLE001
            outs.append(f"EXC:{type(e).__name__}")
    print(json.dumps({"outputs": outs}))


def run_candidate(problem_name, code, inputs):
    job = json.dumps({"problem": problem_name, "code": code, "inputs": inputs})
    try:
        p = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "--worker"],
                           input=job, capture_output=True, text=True, timeout=TIMEOUT_S, cwd=HERE)
    except subprocess.TimeoutExpired:
        return {"timeout": True}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"load_error": (p.stderr or "no output")[-300:]}


def first_mismatch(inputs, got, want):
    for args, g, w in zip(inputs, got, want):
        if g != w:
            return {"input": args, "got": g[:120], "expected": w[:120]}
    return None


def load_candidates(problems):
    import mutate
    cands = []
    for name, prob in problems.items():
        for i, m in enumerate(mutate.mutants(prob["reference"])):
            cands.append(dict(id=f"{name}-mut{i:02d}", problem=name, source="mutation",
                              intended_flaw=m["intended_flaw"], change=m["change"], code=m["code"]))
    cdir = os.path.join(HERE, "candidates")
    if os.path.isdir(cdir):
        for fn in sorted(os.listdir(cdir)):
            if fn.endswith(".jsonl"):
                with open(os.path.join(cdir, fn)) as fh:
                    for line in fh:
                        if line.strip():
                            c = json.loads(line)
                            c.setdefault("source", "llm")
                            c.setdefault("intended_flaw", "claimed:" + c.get("claimed_flaw", "unknown"))
                            c.setdefault("change", c.get("claimed_flaw", ""))
                            cands.append(c)
    return cands


def to_jsonable(inputs):
    # each entry is a 1-tuple wrapping the argument tuple
    return [list(a[0]) for a in inputs]


def main():
    sys.path.insert(0, HERE)
    import problems as P
    rng = random.Random(1007)
    suites = {}
    for name, prob in P.PROBLEMS.items():
        course = to_jsonable(prob["course_tests"])
        adv = to_jsonable(prob["adversarial"](rng))
        ref_c = run_candidate(name, prob["reference"], course)["outputs"]
        ref_a = run_candidate(name, prob["reference"], adv)["outputs"]
        bad = [o for o in ref_c + ref_a if o.startswith("EXC:")]
        assert not bad, f"reference for {name} raised on its own tests: {bad[:3]}"
        suites[name] = (course, adv, ref_c, ref_a)

    rows = []
    for c in load_candidates(P.PROBLEMS):
        course, adv, ref_c, ref_a = suites[c["problem"]]
        incomplete = any(t in c["code"] for t in ("TODO", "NotImplementedError", "...")) and c["source"] != "mutation"
        rc = run_candidate(c["problem"], c["code"], course)
        if "load_error" in rc:
            observed, ex = "load_error", {"error": rc["load_error"][:200]}
        elif rc.get("timeout") or rc["outputs"] != ref_c:
            observed = "course_fail"
            ex = {"input": "course suite", "got": "timeout"} if rc.get("timeout") else first_mismatch(course, rc["outputs"], ref_c)
        else:
            ra = run_candidate(c["problem"], c["code"], adv)
            if ra.get("timeout"):
                observed, ex = "adversarial_only", {"input": "adversarial suite", "got": "timeout"}
            elif ra["outputs"] != ref_a:
                observed, ex = "adversarial_only", first_mismatch(adv, ra["outputs"], ref_a)
            else:
                observed, ex = "no_observed_defect", None
        rows.append(dict(id=c["id"], problem=c["problem"], source=c["source"],
                         intended_flaw=c["intended_flaw"], change=c["change"],
                         incomplete_code=incomplete, observed=observed,
                         counterexample=json.dumps(ex) if ex else "", code=c["code"]))

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "audit.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    write_annotation_sheet(rows)
    write_report(rows, suites)
    print(f"audited {len(rows)} candidates -> results/audit.csv, results/report.md, results/annotation_sheet.csv")


def write_annotation_sheet(rows):
    """Blind sheet for human adjudication: the automated label is NOT shown."""
    rng = random.Random(7)
    sample = rows[:]
    rng.shuffle(sample)
    path = os.path.join(HERE, "results", "annotation_sheet.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "problem", "code", "annotator",
                    "defect_present(yes/no/unsure)", "defect_type", "would_a_novice_notice(1-5)", "notes"])
        for r in sample:
            w.writerow([r["id"], r["problem"], r["code"], "", "", "", "", ""])


def write_report(rows, suites):
    by_obs = Counter(r["observed"] for r in rows)
    by_kind = defaultdict(Counter)
    by_prob = defaultdict(Counter)
    for r in rows:
        by_kind[r["intended_flaw"]][r["observed"]] += 1
        by_prob[r["problem"]][r["observed"]] += 1
    cols = ["course_fail", "adversarial_only", "no_observed_defect", "load_error"]
    n = len(rows)
    L = ["# Flaw-validity audit report", "",
         f"Candidates audited: **{n}** across {len(by_prob)} problems.",
         "Course suite = the few lab-style tests per problem. Adversarial suite = edge cases plus "
         "randomised inputs checked against the reference solution "
         f"({', '.join(f'{k}: {len(v[1])}' for k, v in suites.items())} inputs).", "",
         "## Observed outcome", "", "| outcome | count | share |", "|---|---|---|"]
    for k in cols:
        L.append(f"| {k} | {by_obs[k]} | {by_obs[k] / n:.0%} |")
    L += ["", "## By intended flaw type", "", "| intended flaw | " + " | ".join(cols) + " |",
          "|---|" + "---|" * len(cols)]
    for kind, c in sorted(by_kind.items()):
        L.append(f"| {kind} | " + " | ".join(str(c[k]) for k in cols) + " |")
    L += ["", "## By problem", "", "| problem | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for p, c in sorted(by_prob.items()):
        L.append(f"| {p} | " + " | ".join(str(c[k]) for k in cols) + " |")
    subtle = [r for r in rows if r["observed"] == "adversarial_only"][:5]
    L += ["", "## Examples that pass the lab-style tests but are wrong", ""]
    for r in subtle:
        L += [f"**{r['id']}** ({r['change']})", "", "```python", r["code"].strip(), "```",
              f"Counterexample: `{r['counterexample']}`", ""]
    L += ["## How to read this", "",
          "- `adversarial_only` is the share a lab autograder would have passed. A test-based filter "
          "applied before serving would keep these, but a filter that required the lab tests to fail "
          "would throw them away.",
          "- `no_observed_defect` is not the same as correct. Some are equivalent mutants; others may be "
          "wrong on inputs we did not try. These need human adjudication.",
          "- For mutants the intended flaw is known. For LLM output it is only claimed, so intent and "
          "observed defect are reported in separate columns and never merged.", ""]
    with open(os.path.join(HERE, "results", "report.md"), "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    if "--worker" in sys.argv:
        _worker()
    else:
        main()
