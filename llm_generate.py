"""Optional: generate Navigator-style flawed code with an LLM, for the audit.

NOT RUN in the published results (no API key was used). Requires
`pip install openai` and OPENAI_API_KEY. Writes candidates/llm_<model>.jsonl,
which audit.py picks up automatically.

The prompt follows the paper's public description of the Navigator agent:
introduce a subtle logical oversight or incomplete reasoning, plausibly wrong
rather than randomly wrong. The model's own description of its flaw is stored
as `claimed_flaw`; the audit never treats that claim as ground truth.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import problems as P  # noqa: E402

PROMPT = """You are a pair-programming partner for a data structures course.
Write a Python implementation of `{entry}` for the task below. Introduce exactly
one subtle logical oversight that a student could plausibly make themselves
(plausibly wrong, not randomly wrong). Return JSON with keys "code" (the full
function, no tests) and "claimed_flaw" (one sentence describing the flaw).

Reference behaviour (do not copy it):
{reference}
"""


def main(model="gpt-4o", per_problem=10):
    from openai import OpenAI
    client = OpenAI()
    os.makedirs("candidates", exist_ok=True)
    out = open(f"candidates/llm_{model}.jsonl", "w")
    for name, prob in P.PROBLEMS.items():
        for i in range(per_problem):
            r = client.chat.completions.create(
                model=model, temperature=0.8, response_format={"type": "json_object"},
                messages=[{"role": "user", "content": PROMPT.format(entry=prob["entry"], reference=prob["reference"])}])
            d = json.loads(r.choices[0].message.content)
            out.write(json.dumps({"id": f"{name}-{model}-{i:02d}", "problem": name, "source": f"llm:{model}",
                                  "claimed_flaw": d.get("claimed_flaw", ""), "code": d["code"]}) + "\n")
    out.close()


if __name__ == "__main__":
    main(*(sys.argv[1:2] or []))
