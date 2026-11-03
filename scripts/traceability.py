#!/usr/bin/env python3
"""
Generates the traceability matrix from the repository artifacts:
    acceptance criterion → risks → BDD scenarios → manual test cases → defects (→ last result, if reports exist)

Usage: python3 scripts/traceability.py [reports-folder]   (writes docs/qa/traceability-matrix.md)
The matrix never goes stale: change a scenario, regenerate the matrix.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_artifacts as qa  # noqa: E402

OUT = os.path.join(qa.ROOT, "docs", "qa", "traceability-matrix.md")
ICON = {qa.PASSED: "✓ passed", qa.FAILED: "✗ failed", qa.NOT_RUN: "— not run"}


def build(reports=None):
    criteria, scenarios = qa.features()
    risks, manual, defects = qa.risks(), qa.manual_cases(), qa.defects()
    has_results = bool(reports and os.path.isdir(reports))
    if has_results:
        qa.scenario_results(scenarios, qa.junit_results(reports))

    lines = [
        "# Traceability matrix · QA Lab", "",
        f"Generated automatically by `scripts/traceability.py` on {date.today().isoformat()}. Do not edit by hand.", "",
        "| Acceptance criterion | Risks | BDD scenarios | Manual cases | Defects" + (" | Last result |" if has_results else " |"),
        "| --- | --- | --- | --- | ---" + (" | --- |" if has_results else " |"),
    ]
    uncovered = []
    for ac in criteria:                      # in feature order (validation → matching → settlement → integration)
        scs = [s for s in scenarios if ac in s["acs"]]
        if not scs:
            uncovered.append(ac)
        r = ", ".join(f"{rid} ({risks[rid]['priority']})" for rid in sorted(risks) if ac in risks[rid]["acs"]) or "—"
        sc_txt = "<br>".join(f"{s['name']} (`{s['file']}:{s['line']}`)" for s in scs) or "**no scenario**"
        tc = ", ".join(t for t in sorted(manual) if ac in manual[t]["acs"]) or "—"
        df = ", ".join(f"{d['id']} ({d['status']})" for d in defects if ac in d["acs"]) or "—"
        row = f"| **{ac}** {criteria[ac]['text']} | {r} | {sc_txt} | {tc} | {df}"
        if has_results:
            row += f" | {ICON[qa.combine(s.get('result', qa.NOT_RUN) for s in scs)]}"
        lines.append(row + " |")

    automated = len(criteria) - len(uncovered)
    covered_risks = sum(1 for r in risks.values() if any(a not in uncovered for a in r["acs"]))
    lines += [
        "",
        "## Coverage",
        "",
        f"- Acceptance criteria: **{len(criteria)}**, with an automated scenario: **{automated}** "
        f"({round(100 * automated / max(len(criteria), 1))}%).",
        f"- Business risks covered by criteria with a scenario: **{covered_risks} of {len(risks)}**.",
        f"- Manual test cases: **{len(manual)}** · Defects logged: **{len(defects)}**.",
    ]
    if uncovered:
        lines.append(f"- Criteria without an automated scenario: {', '.join(uncovered)}.")
    return "\n".join(lines) + "\n"


def main():
    text = build(sys.argv[1] if len(sys.argv) > 1 else None)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Matrix written to {os.path.relpath(OUT, qa.ROOT)}")


if __name__ == "__main__":
    main()
