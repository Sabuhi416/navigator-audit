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

## Demo run (40 mutants, 5 problems)

This run checks that the pipeline works. It is not a finding.

| observed | count |
|---|---|
| fails the lab-style tests | 32 |
| passes lab-style tests, fails adversarial tests | 7 |
| no observed defect | 1 |

- I wrote both the mutants and the lab-style tests, so "7 of 40 pass the lab-style tests" measures
  how weak those few tests are. It says nothing about AlgoGPT's tests or its Navigator output.
- The "no observed defect" case is an equivalent mutant (`<` changed to `<=` after an `==` check
  has already returned), a known artefact of mutation testing.
- For mutants the change is known, so the annotation sheet adds nothing here. It exists for
  Navigator outputs, where the intended flaw is unknown and tests are incomplete.
- `llm_generate.py` would show how GPT-4o flaws behave under my own prompts and problems. That
  is still not Navigator, which uses its own prompts and scales flaws to the student's instruction.

## Limitations

- Passing tests does not prove correctness, and failing tests shows a defect, not intent.
- The adversarial suites are random differential tests against one reference; they can miss
  defects that need specific structures.
- Nothing here measures how hard a defect is for a student to see. Test results are not a proxy
  for that. No student data is used.

## Run

```
python3 audit.py
python3 agreement.py results/annotation_A.csv results/annotation_B.csv   # after two people annotate
```

Python 3.9+, standard library only (`openai` only for `llm_generate.py`).
