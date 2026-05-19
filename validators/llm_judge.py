import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RAW_OUTPUTS_PATH = "results/raw_outputs.json"
OUTPUT_PATH = "results/judged_results.json"

MODEL = "gpt-4.1-mini"


JUDGE_PROMPT = """
You are an enterprise-grade AI evaluation judge working in a highly regulated financial environment.

Your task is to STRICTLY evaluate the quality, reliability, factual grounding, and business usefulness of an LLM-generated report.

Assume the report may be used for executive financial decision-making.

You must aggressively penalize:
- unsupported claims,
- invented KPI values,
- vague recommendations,
- weak financial reasoning,
- contradictions,
- missing grounding,
- unstable logic,
- generic consulting language,
- and shallow analysis.

Scoring must be VERY strict.

A score of:
- 10 = exceptional enterprise-grade output
- 8 = strong and reliable
- 6 = acceptable but weak
- 4 = unreliable
- 2 = poor
- 0 = unusable

Most outputs should NOT receive 9 or 10.

Evaluate from 0 to 10:

1. Structure Compliance
2. Business Quality
3. KPI Grounding Accuracy
4. Actionability
5. Hallucination Risk
6. Prompt Angle Compliance
7. Executive Readability
8. Financial / Strategic Reasoning
9. Consistency of Logic
10. Recommendation Quality

IMPORTANT:
- Penalize generic business statements.
- Penalize unsupported benchmarking claims.
- Penalize weak causal reasoning.
- Penalize repetitive language.
- Penalize conclusions not supported by evidence.
- Penalize unrealistic certainty.
- Penalize instability between sections.

Reward:
- grounded reasoning,
- nuanced analysis,
- realistic uncertainty,
- strong KPI linkage,
- measurable recommendations,
- executive-level clarity,
- and internal consistency.

Return ONLY valid JSON.

Format:

{
  "structure_compliance": 0,
  "business_quality": 0,
  "kpi_grounding_accuracy": 0,
  "actionability": 0,
  "hallucination_risk": 0,
  "prompt_angle_compliance": 0,
  "executive_readability": 0,
  "financial_reasoning": 0,
  "logic_consistency": 0,
  "recommendation_quality": 0,
  "overall_score": 0,
  "verdict": "PASS or FAIL",
  "strengths": [],
  "weaknesses": [],
  "hallucination_flags": [],
  "drift_risk_flags": [],
  "improvement_recommendations": []
}
"""


def safe_json_loads(text):
    """
    Tries to parse JSON returned by the judge.
    If the model accidentally wraps JSON in text, this attempts to extract the JSON object.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        possible_json = text[start:end + 1]
        try:
            return json.loads(possible_json)
        except json.JSONDecodeError:
            pass

    return {
        "error": "INVALID_JSON_RETURNED",
        "raw_response": text
    }


def normalize_judge_result(result):
    """
    Ensures expected keys exist and computes verdict if missing.
    """
    expected_keys = [
        "structure_compliance",
        "business_quality",
        "kpi_grounding_accuracy",
        "actionability",
        "hallucination_risk",
        "prompt_angle_compliance",
        "executive_readability",
        "financial_reasoning",
        "logic_consistency",
        "recommendation_quality",
        "overall_score",
        "verdict",
        "strengths",
        "weaknesses",
        "hallucination_flags",
        "drift_risk_flags",
        "improvement_recommendations"
    ]

    if "error" in result:
        return result

    for key in expected_keys:
        if key not in result:
            if key in [
                "strengths",
                "weaknesses",
                "hallucination_flags",
                "drift_risk_flags",
                "improvement_recommendations"
            ]:
                result[key] = []
            elif key == "verdict":
                result[key] = "FAIL"
            else:
                result[key] = 0

    numeric_fields = [
        "structure_compliance",
        "business_quality",
        "kpi_grounding_accuracy",
        "actionability",
        "hallucination_risk",
        "prompt_angle_compliance",
        "executive_readability",
        "financial_reasoning",
        "logic_consistency",
        "recommendation_quality"
    ]

    scores = []

    for field in numeric_fields:
        try:
            value = float(result[field])
            value = max(0, min(10, value))
            result[field] = value
            scores.append(value)
        except (ValueError, TypeError):
            result[field] = 0
            scores.append(0)

    calculated_score = round(sum(scores) / len(scores), 2)

    try:
        result["overall_score"] = float(result["overall_score"])
    except (ValueError, TypeError):
        result["overall_score"] = calculated_score

    result["overall_score"] = round(result["overall_score"], 2)

    if result["overall_score"] >= 8:
        result["verdict"] = "PASS"
    else:
        result["verdict"] = "FAIL"

    return result


def evaluate_output(prompt_name, run_number, output_text):
    evaluation_request = f"""
PROMPT NAME:
{prompt_name}

RUN NUMBER:
{run_number}

OUTPUT TO EVALUATE:
{output_text}
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": JUDGE_PROMPT
            },
            {
                "role": "user",
                "content": evaluation_request
            }
        ],
        temperature=0
    )

    raw_text = response.output_text.strip()
    parsed = safe_json_loads(raw_text)
    normalized = normalize_judge_result(parsed)

    return normalized


def main():
    raw_path = Path(RAW_OUTPUTS_PATH)

    if not raw_path.exists():
        raise FileNotFoundError(
            f"Could not find {RAW_OUTPUTS_PATH}. Run validate_prompt_suite.py first."
        )

    raw_outputs = json.loads(raw_path.read_text(encoding="utf-8"))

    judged_results = []

    for item in raw_outputs:
        prompt_name = item.get("prompt_name", "UNKNOWN_PROMPT")
        run_number = item.get("run_number", "UNKNOWN_RUN")
        output_text = item.get("output", "")

        print(f"Evaluating {prompt_name} run {run_number}")

        try:
            judged = evaluate_output(
                prompt_name=prompt_name,
                run_number=run_number,
                output_text=output_text
            )

        except Exception as e:
            judged = {
                "error": "JUDGE_CALL_FAILED",
                "message": str(e),
                "overall_score": 0,
                "verdict": "FAIL"
            }

        judged_results.append({
            "prompt_name": prompt_name,
            "run_number": run_number,
            "judge_result": judged
        })

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(exist_ok=True)

    output_path.write_text(
        json.dumps(judged_results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nDONE.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
