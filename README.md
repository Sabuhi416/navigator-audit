# navigator-flaw-audit

A small, offline harness for one question about AI tutors that inject deliberate flaws
(for example AlgoGPT's Navigator mode, described in Balakrishnan et al., *Beyond the Perfect
Assistant*, DIS Companion '26): **is the code a student is asked to judge actually wrong, and
how hard is the defect to see?**

The paper notes that not every Navigator output can be verified as an intentional flaw rather
than a model mistake. This harness does not try to recover intent. It separates the two
questions and answers the one that can be answered from the code:

| column | meaning |
|---|---|
| `intended_flaw` | what the generator says it did. Known for mutants, only *claimed* for LLM output |
| `observed` | what testing shows: `course_fail`, `adversarial_only`, `no_observed_defect`, `load_error` |

Nothing is filtered out. Code that passes the lab-style tests but is wrong (`adversarial_only`)
is kept, because those are the flaws a student is least likely to catch, and code with no
observed defect goes to human review instead of being called correct.

## What is in it

- `problems.py`: five standard public DSA exercises (binary search, middle of a linked list,
  reverse a linked list, validate a BST, level-order traversal). Each has a reference solution,
  a few lab-style tests, and an adversarial suite: edge cases plus 200 to 300 random inputs
  checked against the reference.
- `mutate.py`: deterministic flaw generator, one AST mutation per site (comparison and boundary
  changes, off-by-one constants, dropped branches, dropped pointer updates, wrong pointer).
- `llm_generate.py`: optional LLM generator using a prompt modelled on the paper's description
  of the Navigator agent. **Not run for the results below**; needs an API key.
- `audit.py`: runs every candidate in a separate process with a timeout and writes
  `results/audit.csv`, `results/report.md` and a blind `results/annotation_sheet.csv`
  (automated label hidden) for human adjudication.
- `agreement.py`: Cohen's kappa between two annotators, and between each annotator and the
  automated label.

## First run (40 mutants, 5 problems)

| observed | count | share |
|---|---|---|
| fails the lab-style tests | 32 | 80% |
| passes lab tests, fails adversarial tests | 7 | 18% |
| no observed defect | 1 | 2% |

- 7 of 40 mutants would pass a typical lab autograder while being wrong. Example: in binary
  search, `hi = mid - 2` passes the three lab cases and fails on an 18-element array.
- The single "no observed defect" case is an equivalent mutant: changing `<` to `<=` after an
  `==` check has already returned. Its intended flaw is real; its observed defect is none. That
  is the intent-versus-defect gap in one example.
- These are mechanical mutants, not LLM output, so the shares say nothing yet about how an LLM
  Navigator behaves. That comparison is the next step.

## Limitations

- Passing tests does not prove correctness, and failing tests shows a defect, not intent.
- The adversarial suites are random differential tests against one reference; they can miss
  defects that need specific structures.
- "How visible is this defect to a novice" is not measured here. The annotation sheet collects
  a human rating for it; nothing in this repo uses student data.

## Run

```
python3 audit.py
python3 agreement.py results/annotation_A.csv results/annotation_B.csv   # after two people annotate
```

Python 3.9+, standard library only (`openai` only for `llm_generate.py`).
