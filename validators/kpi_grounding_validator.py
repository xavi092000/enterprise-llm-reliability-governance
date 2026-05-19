import json
import re
from pathlib import Path

RAW_OUTPUTS_PATH = "results/raw_outputs.json"
GROUND_TRUTH_PATH = "ground_truth_kpis.json"
OUTPUT_PATH = "results/kpi_grounding_results.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_numbers(text):
    patterns = [
        r"-?\d+\.\d+%",
        r"-?\d+%",
        r"US\$ ?\d+\.\d+ ?billion",
        r"US\$ ?\d+ ?billion",
        r"US\$ ?\d+\.\d+ ?trillion",
        r"US\$ ?\d+ ?trillion",
        r"\d+\.\d+",
        r"\d+"
    ]

    matches = []

    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    return list(set(matches))


def normalize_number(value):
    value = str(value).lower()
    value = value.replace("us$", "")
    value = value.replace("%", "")
    value = value.replace("billion", "")
    value = value.replace("trillion", "")
    value = value.strip()

    try:
        return float(value)
    except ValueError:
        return None


def find_ground_truth_hits(output_text, ground_truth):
    extracted = extract_numbers(output_text)
    extracted_values = [normalize_number(x) for x in extracted]
    extracted_values = [x for x in extracted_values if x is not None]

    hits = []
    misses = []

    for kpi_name, expected_value in ground_truth.items():
        found = False

        for generated_value in extracted_values:
            tolerance = max(0.2, abs(expected_value) * 0.02)

            if abs(generated_value - expected_value) <= tolerance:
                found = True
                break

        if found:
            hits.append(kpi_name)
        else:
            misses.append(kpi_name)

    score = len(hits) / len(ground_truth) if ground_truth else 0

    return {
        "kpi_grounding_score": round(score, 2),
        "hits": hits,
        "misses": misses,
        "extracted_numbers": extracted
    }


def main():
    raw_outputs = load_json(RAW_OUTPUTS_PATH)
    ground_truth = load_json(GROUND_TRUTH_PATH)

    results = []

    for item in raw_outputs:
        prompt_name = item["prompt_name"]
        run_number = item["run_number"]
        output_text = item["output"]

        print(f"Validating KPI grounding: {prompt_name} run {run_number}")

        validation = find_ground_truth_hits(output_text, ground_truth)

        results.append({
            "prompt_name": prompt_name,
            "run_number": run_number,
            "kpi_grounding": validation
        })

    Path(OUTPUT_PATH).write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nDONE.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()