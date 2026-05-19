import json
from pathlib import Path

RAW_OUTPUTS_PATH = "results/raw_outputs.json"
OUTPUT_PATH = "results/source_coverage_results.json"

PROMPT_KPI_REQUIREMENTS = {
    "PEPD1": ["growth", "revenue", "ROI"],
    "PEPD3": ["MTTR", "DSO", "liquidity", "risk"],
    "PEPD4": ["OPEX", "revenue per employee", "efficiency"],
    "PEPD5": ["cloud adoption", "AI adoption", "digital"],
    "PEPD6": ["NRR", "GRR", "CSAT", "churn"],
    "PEPD7": ["Scope 1", "Scope 2", "Scope 3", "ESG"],
    "PEPD8": ["international revenue", "HHI", "localization"],
    "PEPD9": ["R&D", "new products", "ARR"],
    "PEPD10": ["CCC", "DSO", "Current Ratio", "Quick Ratio"],
    "PEPD11": ["scenario", "baseline", "optimistic", "pessimistic"],
    "PEPS": ["ROI", "benchmark"]
}


def calculate_risk_level(score):
    if score >= 0.8:
        return "LOW"
    elif score >= 0.5:
        return "MEDIUM"
    else:
        return "HIGH"


def main():
    raw_outputs = json.loads(
        Path(RAW_OUTPUTS_PATH).read_text(encoding="utf-8")
    )

    coverage_results = []

    for item in raw_outputs:
        prompt_name = item["prompt_name"]
        output = item["output"]

        required_kpis = PROMPT_KPI_REQUIREMENTS.get(prompt_name, [])

        found = []
        missing = []

        lower_output = output.lower()

        for kpi in required_kpis:
            if kpi.lower() in lower_output:
                found.append(kpi)
            else:
                missing.append(kpi)

        coverage_score = (
            len(found) / len(required_kpis)
            if required_kpis else 0
        )

        result = {
            "prompt_name": prompt_name,
            "run_number": item["run_number"],
            "required_kpis": required_kpis,
            "found_kpis": found,
            "missing_kpis": missing,
            "coverage_score": round(coverage_score, 2),
            "risk_level": calculate_risk_level(coverage_score)
        }

        coverage_results.append(result)

        print(
            f"{prompt_name} run {item['run_number']} "
            f"-> coverage={coverage_score:.2f}"
        )

    Path(OUTPUT_PATH).write_text(
        json.dumps(coverage_results, indent=2),
        encoding="utf-8"
    )

    print("\nDONE.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()