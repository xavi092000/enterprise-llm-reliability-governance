from dotenv import load_dotenv
load_dotenv()
import os
import csv
import json
import time
import re
from pathlib import Path
from datetime import datetime
from openai import OpenAI


# =========================
# CONFIGURATION
# =========================

PDF_PATH = "deloitte-global-powers-of-retailing-2025.pdf"
PROMPTS_DIR = Path("prompts")
RESULTS_DIR = Path("results")

MODEL = "gpt-4.1-mini"
RUNS_PER_PROMPT = 5

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EXPECTED_SECTIONS = [
    "Executive Summary",
    "Key Insights",
    "Risks & Opportunities",
    "Recommendations",
    "Conclusion",
]

PROMPT_ANGLES = {
    "PEPD1": "Revenue Growth Acceleration",
    "PEPD2": "Growth Capture",
    "PEPD3": "Risk Mitigation",
    "PEPD4": "Operational Efficiency",
    "PEPD5": "Digital Transformation",
    "PEPD6": "Customer Retention & Satisfaction",
    "PEPD7": "ESG Compliance & Sustainability",
    "PEPD8": "Global Expansion & Diversification",
    "PEPD9": "Innovation Pipeline & New Products",
    "PEPD10": "Cash Flow & Liquidity Management",
    "PEPD11": "Scenario-based Analysis",
    "PEPS": "ROI Benchmark Superiority",
}


# =========================
# UTILS
# =========================

def ensure_dirs():
    RESULTS_DIR.mkdir(exist_ok=True)
    PROMPTS_DIR.mkdir(exist_ok=True)


def load_prompt_files(): [
         PROMPTS_DIR / "PEPD1.txt",
         PROMPTS_DIR / "PEPD11.txt"
]
    
    if not prompt_files:
        raise FileNotFoundError(
            "Aucun prompt trouvé. Crée un dossier 'prompts' et ajoute tes prompts en fichiers .txt."
        )

    prompts = []

    for file in prompt_files:
        prompts.append({
            "name": file.stem,
            "path": str(file),
            "content": file.read_text(encoding="utf-8")
        })

    return prompts


def upload_pdf(pdf_path):
    if not Path(pdf_path).exists():
        raise FileNotFoundError(
            f"PDF introuvable: {pdf_path}. Mets le PDF dans le même dossier que le script."
        )

    uploaded_file = client.files.create(
        file=open(pdf_path, "rb"),
        purpose="assistants"
    )

    return uploaded_file.id


def call_model(prompt_name, prompt_content, file_id):
    user_instruction = f"""
You are testing the following prompt against a real Deloitte report.

PROMPT NAME:
{prompt_name}

PROMPT TO EXECUTE:
{prompt_content}

TASK:
Use the attached Deloitte Global Powers of Retailing 2025 PDF as the only source of truth.

Rules:
- Do not invent facts.
- If information is missing, use DATA_NOT_AVAILABLE.
- Cite page references when possible.
- Produce the output requested by the prompt.
- Keep the answer business-ready and concise.
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": file_id
                    },
                    {
                        "type": "input_text",
                        "text": user_instruction
                    }
                ]
            }
        ],
        temperature=0.2
    )

    return response.output_text


def has_expected_sections(text):
    found = 0
    for section in EXPECTED_SECTIONS:
        if re.search(rf"#+\s*{re.escape(section)}", text, re.IGNORECASE):
            found += 1
    return found, len(EXPECTED_SECTIONS)


def detect_angle(prompt_name, text):
    for key, angle in PROMPT_ANGLES.items():
        if key.lower() in prompt_name.lower():
            return angle, angle.lower() in text.lower()

    return "UNKNOWN", None


def count_data_not_available(text):
    return text.count("DATA_NOT_AVAILABLE")


def has_actionable_recommendations(text):
    patterns = [
        r"\[\s?\]",
        r"increase .* by \d+",
        r"reduce .* by \d+",
        r"within \d+",
        r"\d+%",
        r"months",
        r"quarter",
    ]

    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def has_kpis(text):
    patterns = [
        r"\d+%",
        r"US\$",
        r"CAGR",
        r"margin",
        r"revenue",
        r"ROI",
        r"DSO",
        r"DPO",
        r"CCC",
        r"NRR",
        r"GRR",
        r"MTTR",
    ]

    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def has_no_obvious_hallucination_markers(text):
    bad_markers = [
        "as everyone knows",
        "clearly proves",
        "guaranteed",
        "without any data",
        "I assume",
        "probably",
    ]

    lowered = text.lower()
    return not any(marker in lowered for marker in bad_markers)


def evaluate_output(prompt_name, output_text):
    sections_found, sections_total = has_expected_sections(output_text)
    angle, angle_present = detect_angle(prompt_name, output_text)

    checks = {
        "sections_score": sections_found / sections_total,
        "format_pass": sections_found >= 4,
        "angle": angle,
        "angle_pass": angle_present if angle_present is not None else True,
        "has_kpis": has_kpis(output_text),
        "has_actionable_recommendations": has_actionable_recommendations(output_text),
        "data_not_available_count": count_data_not_available(output_text),
        "hallucination_marker_pass": has_no_obvious_hallucination_markers(output_text),
    }

    pass_count = 0
    total = 5

    if checks["format_pass"]:
        pass_count += 1

    if checks["angle_pass"]:
        pass_count += 1

    if checks["has_kpis"]:
        pass_count += 1

    if checks["has_actionable_recommendations"]:
        pass_count += 1

    if checks["hallucination_marker_pass"]:
        pass_count += 1

    checks["final_score"] = round(pass_count / total, 2)
    checks["verdict"] = "PASS" if checks["final_score"] >= 0.80 else "FAIL"

    return checks


def write_json(data, filename):
    path = RESULTS_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_csv(rows, filename):
    path = RESULTS_DIR / filename

    if not rows:
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return path


def generate_markdown_report(summary_rows):
    lines = []
    lines.append("# Prompt Validation Report")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"Model: {MODEL}")
    lines.append(f"Runs per prompt: {RUNS_PER_PROMPT}")
    lines.append(f"Source document: {PDF_PATH}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Prompt | Runs | Passes | Pass Rate | Avg Score | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---|")

    grouped = {}

    for row in summary_rows:
        grouped.setdefault(row["prompt_name"], []).append(row)

    for prompt_name, rows in grouped.items():
        runs = len(rows)
        passes = sum(1 for r in rows if r["verdict"] == "PASS")
        pass_rate = passes / runs
        avg_score = sum(float(r["final_score"]) for r in rows) / runs
        verdict = "PASS" if pass_rate >= 0.80 else "FAIL"

        lines.append(
            f"| {prompt_name} | {runs} | {passes} | {pass_rate:.0%} | {avg_score:.2f} | {verdict} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- PASS rate ≥ 80% = prompt considered reliable.")
    lines.append("- FAIL = prompt needs revision, stronger constraints, or clearer expected output.")
    lines.append("- This report validates structure, angle compliance, KPI usage, actionability, and basic hallucination-risk markers.")
    lines.append("")
    lines.append("## Morgan Stanley Positioning")
    lines.append("")
    lines.append("This benchmark demonstrates a repeatable LLM evaluation workflow for prompt stability, output consistency, KPI extraction, and business-readiness testing against a real strategic report.")

    path = RESULTS_DIR / "prompt_validation_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# =========================
# MAIN
# =========================

def main():
    ensure_dirs()

    print("Loading prompts...")
    prompts = load_prompt_files()

    print("Uploading PDF to OpenAI...")
    file_id = upload_pdf(PDF_PATH)

    all_results = []
    csv_rows = []

    for prompt in prompts:
        prompt_name = prompt["name"]
        prompt_content = prompt["content"]

        print(f"\nTesting prompt: {prompt_name}")

        for run_number in range(1, RUNS_PER_PROMPT + 1):
            print(f"  Run {run_number}/{RUNS_PER_PROMPT}...")

            try:
                output_text = call_model(prompt_name, prompt_content, file_id)
                evaluation = evaluate_output(prompt_name, output_text)

                result = {
                    "prompt_name": prompt_name,
                    "run_number": run_number,
                    "output": output_text,
                    "evaluation": evaluation,
                    "timestamp": datetime.now().isoformat(timespec="seconds")
                }

                all_results.append(result)

                csv_rows.append({
                    "prompt_name": prompt_name,
                    "run_number": run_number,
                    "sections_score": evaluation["sections_score"],
                    "angle": evaluation["angle"],
                    "angle_pass": evaluation["angle_pass"],
                    "has_kpis": evaluation["has_kpis"],
                    "has_actionable_recommendations": evaluation["has_actionable_recommendations"],
                    "data_not_available_count": evaluation["data_not_available_count"],
                    "hallucination_marker_pass": evaluation["hallucination_marker_pass"],
                    "final_score": evaluation["final_score"],
                    "verdict": evaluation["verdict"],
                })

                time.sleep(1)

            except Exception as e:
                print(f"ERROR on {prompt_name}, run {run_number}: {e}")

                csv_rows.append({
                    "prompt_name": prompt_name,
                    "run_number": run_number,
                    "sections_score": 0,
                    "angle": "ERROR",
                    "angle_pass": False,
                    "has_kpis": False,
                    "has_actionable_recommendations": False,
                    "data_not_available_count": 0,
                    "hallucination_marker_pass": False,
                    "final_score": 0,
                    "verdict": "ERROR",
                })

    raw_path = write_json(all_results, "raw_outputs.json")
    csv_path = write_csv(csv_rows, "summary_results.csv")
    report_path = generate_markdown_report(csv_rows)

    print("\nDONE.")
    print(f"Raw outputs: {raw_path}")
    print(f"CSV summary: {csv_path}")
    print(f"Markdown report: {report_path}")


if __name__ == "__main__":
    main()