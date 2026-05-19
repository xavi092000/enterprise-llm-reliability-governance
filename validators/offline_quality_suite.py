import json
import re
from pathlib import Path
from collections import defaultdict

RAW_OUTPUTS = Path("results/raw_outputs.json")
JUDGED_RESULTS = Path("results/judged_results.json")
OUT = Path("results/offline_quality_report.json")

PROMPT_KPI_REQUIREMENTS = {
    "PEPD1": ["revenue", "growth", "walmart", "amazon", "costco"],
    "PEPD3": ["risk", "liquidity", "mitigation", "DATA_NOT_AVAILABLE"],
    "PEPD4": ["efficiency", "automation", "margin", "DATA_NOT_AVAILABLE"],
    "PEPD5": ["digital", "AI", "cloud", "DATA_NOT_AVAILABLE"],
    "PEPD6": ["retention", "satisfaction", "churn", "DATA_NOT_AVAILABLE"],
    "PEPD7": ["ESG", "Scope", "sustainability", "DATA_NOT_AVAILABLE"],
    "PEPD8": ["global", "international", "geography", "diversification"],
    "PEPD9": ["innovation", "new products", "R&D", "DATA_NOT_AVAILABLE"],
    "PEPD10": ["cash flow", "liquidity", "working capital", "DATA_NOT_AVAILABLE"],
    "PEPD11": ["baseline", "optimistic", "pessimistic", "scenario"],
    "PEPS": ["ROI", "benchmark", "DATA_NOT_AVAILABLE"]
}

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Key Insights",
    "Risks & Opportunities",
    "Recommendations",
    "Conclusion"
]

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def section_score(text):
    found = [s for s in REQUIRED_SECTIONS if s.lower() in text.lower()]
    return round(len(found) / len(REQUIRED_SECTIONS), 2), found

def coverage_score(prompt, text):
    reqs = PROMPT_KPI_REQUIREMENTS.get(prompt, [])
    found = [r for r in reqs if r.lower() in text.lower()]
    missing = [r for r in reqs if r.lower() not in text.lower()]
    score = round(len(found) / len(reqs), 2) if reqs else 0
    risk = "LOW" if score >= 0.8 else "MEDIUM" if score >= 0.5 else "HIGH"
    return score, risk, found, missing

def json_block_validity(text):
    blocks = re.findall(r"\{[\s\S]*?\}", text)
    valid = 0
    invalid = 0

    for block in blocks:
        try:
            json.loads(block)
            valid += 1
        except Exception:
            invalid += 1

    return {
        "json_blocks_found": len(blocks),
        "valid_json_blocks": valid,
        "invalid_json_blocks": invalid
    }

def lexical_drift(outputs):
    grouped = defaultdict(list)
    for item in outputs:
        grouped[item["prompt_name"]].append(item["output"])

    results = {}

    for prompt, texts in grouped.items():
        if len(texts) < 2:
            results[prompt] = {"drift_score": 0, "stability": "UNKNOWN"}
            continue

        word_sets = []
        for t in texts:
            words = set(re.findall(r"\b[a-zA-Z]{4,}\b", t.lower()))
            word_sets.append(words)

        similarities = []
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                a, b = word_sets[i], word_sets[j]
                sim = len(a & b) / len(a | b) if a | b else 0
                similarities.append(sim)

        avg_sim = sum(similarities) / len(similarities)
        drift = round(1 - avg_sim, 2)

        stability = "HIGH" if avg_sim >= 0.65 else "MEDIUM" if avg_sim >= 0.45 else "LOW"

        results[prompt] = {
            "average_similarity": round(avg_sim, 2),
            "drift_score": drift,
            "stability": stability
        }

    return results

def judge_summary():
    if not JUDGED_RESULTS.exists():
        return {}

    judged = load_json(JUDGED_RESULTS)
    grouped = defaultdict(list)

    for item in judged:
        score = item.get("judge_result", {}).get("overall_score")
        verdict = item.get("judge_result", {}).get("verdict")
        if score is not None:
            grouped[item["prompt_name"]].append((score, verdict))

    summary = {}
    for prompt, rows in grouped.items():
        scores = [float(s) for s, _ in rows]
        passes = sum(1 for _, v in rows if v == "PASS")
        summary[prompt] = {
            "avg_judge_score": round(sum(scores) / len(scores), 2),
            "pass_rate": round(passes / len(rows), 2),
            "runs": len(rows)
        }

    return summary

def main():
    outputs = load_json(RAW_OUTPUTS)

    report = {
        "per_run_checks": [],
        "drift_analysis": lexical_drift(outputs),
        "judge_summary": judge_summary()
    }

    for item in outputs:
        prompt = item["prompt_name"]
        text = item["output"]

        sec_score, sections_found = section_score(text)
        cov_score, risk, found, missing = coverage_score(prompt, text)
        json_check = json_block_validity(text)

        report["per_run_checks"].append({
            "prompt_name": prompt,
            "run_number": item["run_number"],
            "section_score": sec_score,
            "sections_found": sections_found,
            "source_coverage_score": cov_score,
            "source_coverage_risk": risk,
            "found_terms": found,
            "missing_terms": missing,
            "json_validity": json_check,
            "data_not_available_count": text.count("DATA_NOT_AVAILABLE")
        })

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("DONE.")
    print(f"Saved to: {OUT}")

if __name__ == "__main__":
    main()