
$promptsDir = Join-Path $PSScriptRoot "prompts"

$files = @(
  "PEPD3.txt",
  "PEPD4.txt",
  "PEPD5.txt",
  "PEPD6.txt",
  "PEPD7.txt",
  "PEPD8.txt",
  "PEPD9.txt",
  "PEPD10.txt",
  "PEPD11.txt",
  "PEPS.txt"
)

$block = @"

---

## Enterprise Reliability Rules

- Do not invent missing KPIs.
- Do not infer financial impact unless the source explicitly supports it.
- If using a proxy, label it as PROXY_METRIC.
- For every PROXY_METRIC, explain why it is being used, what it can prove, and what it cannot prove.
- If a claim is unusually large or operationally surprising, label it as SOURCE_REPORTED_CLAIM and state: "Source-reported claim; requires independent validation before executive use."
- Do not treat extraordinary claims as proven causal impact.
- Avoid generic consulting language.
- Every strategic claim must be tied to a verified KPI, source-supported statement, PROXY_METRIC, or DATA_NOT_AVAILABLE.

---

## Data Limitations

List:
- unavailable KPIs,
- weak proxies,
- assumptions,
- evidence gaps,
- and what additional data would be needed for executive-grade confidence.

---

## Recommendation Quality Rules

Each recommendation must include:
- action,
- owner/function,
- KPI impacted,
- timeline,
- expected measurable outcome,
- evidence confidence: HIGH / MEDIUM / LOW.

---

## Evidence Confidence

At the end of the report, include:

{
  "evidence_confidence": {
    "financial_kpis": "",
    "operational_kpis": "",
    "strategic_claims": "",
    "recommendations": ""
  }
}

"@

foreach ($file in $files) {
    $path = Join-Path $promptsDir $file

    if (Test-Path $path) {
        $content = Get-Content $path -Raw -Encoding UTF8

        if ($content -notmatch "## Enterprise Reliability Rules") {
            $updated = $content -replace "## Auto-check", "$block`r`n## Auto-check"
            Set-Content -Path $path -Value $updated -Encoding UTF8
            Write-Host "Updated: $file"
        }
        else {
            Write-Host "Skipped already updated: $file"
        }
    }
    else {
        Write-Host "Missing file: $path"
    }
}