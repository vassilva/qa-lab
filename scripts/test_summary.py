#!/usr/bin/env python3
"""
Test report for the go/no-go decision.

Reads the JUnit XML reports in a folder (pytest and behave) and the repository's QA artifacts, and writes:
  <folder>/test-summary.md   text summary (also printed on screen / in the Jenkins log)
  <folder>/index.html        report: progress, acceptance criteria coverage, risks, defects

Usage: python3 scripts/test_summary.py [folder] [version]
Exits with code 1 if any test failed or there are no results.
"""

import glob
import html
import os
import xml.etree.ElementTree as ET
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_artifacts as qa  # noqa: E402

OPEN_STATES = ("New", "In analysis", "Confirmed", "In progress", "Fixed", "In retest", "Reopened", "Open")
P, F, S, N = qa.PASSED, qa.FAILED, qa.SKIPPED, qa.NOT_RUN


def analyse(folder):
    cases = qa.junit_results(folder)
    criteria, scenarios = qa.features()
    qa.scenario_results(scenarios, cases)
    risks, defects = qa.risks(), qa.defects()

    suites = {}
    for c in cases:
        s = suites.setdefault(c["suite"], Counter())
        s["total"] += 1
        s[c["state"]] += 1
    ac_status = {ac: qa.combine(s["result"] for s in scenarios if ac in s["acs"]) for ac in criteria}
    risk_status = {rid: qa.combine(ac_status.get(a, N) for a in r["acs"]) for rid, r in risks.items()}
    coverage = None
    for path in glob.glob(os.path.join(folder, "**", "coverage.xml"), recursive=True):
        try:
            coverage = round(100 * float(ET.parse(path).getroot().get("line-rate", 0)), 1)
        except (ET.ParseError, ValueError):
            pass
    training = [d for d in defects if "challenge mode" in d["status"]]
    open_defects = [d for d in defects if d["status"].startswith(OPEN_STATES) and d not in training]
    failures = [c for c in cases if c["state"] == F]
    return dict(cases=cases, suites=suites, criteria=criteria, ac_status=ac_status, risks=risks,
                risk_status=risk_status, coverage=coverage, open_defects=open_defects, training=training, failures=failures)


def recommendation(a):
    if not a["cases"]:
        return "NO RESULTS", "No test results were found."
    critical_fail = [r for r, s in a["risk_status"].items() if s == F and a["risks"][r]["priority"] in ("Critical", "High")]
    if a["failures"] or critical_fail:
        return "NO-GO", f"{len(a['failures'])} failed test(s); {len(critical_fail)} critical/high risk(s) with failures."
    return "GO", "All automated tests passed. Check the release checklist before approving."


def markdown(a, version):
    decision, reason = recommendation(a)
    lines = [f"# Test summary · version {version}", "",
             "| Suite | Total | Passed | Failed | Skipped |", "| --- | ---: | ---: | ---: | ---: |"]
    tot = Counter()
    for name, s in sorted(a["suites"].items()):
        lines.append(f"| {name} | {s['total']} | {s[P]} | {s[F]} | {s[S]} |")
        tot.update(s)
    lines.append(f"| **Total** | **{tot['total']}** | **{tot[P]}** | **{tot[F]}** | **{tot[S]}** |")
    acs = Counter(a["ac_status"].values())
    if a["coverage"] is not None:
        lines += ["", f"Code coverage (component and API tests): {a['coverage']}%"]
    lines += ["", f"Acceptance criteria: {acs[P]} passed · {acs[F]} failed · "
                  f"{acs[N]} not run (of {len(a['ac_status'])})."]
    if a["failures"]:
        lines += ["", "## Failed tests"] + [f"- {c['class']} › {c['name']}" for c in a["failures"]]
    lines += ["", f"**Recommendation: {decision}** · {reason}"]
    return "\n".join(lines) + "\n"


def page(a, version):
    decision, reason = recommendation(a)
    e = html.escape
    color = {"GO": "#2f9e6e", "NO-GO": "#d9534f"}.get(decision, "#b07a1e")
    badge = {P: "✓ passed", F: "✗ failed", N: "— not run"}

    def table(head, rows):
        return ("<table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr></thead><tbody>" +
                "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")

    def state(st):
        return f'<span class="{st.replace(" ", "-")}">{badge[st]}</span>'

    suites = [[e(n), s["total"], s[P], s[F], s[S]] for n, s in sorted(a["suites"].items())]
    acs = [[f"<b>{e(ac)}</b>", e(a["criteria"][ac]["text"]), state(st)] for ac, st in a["ac_status"].items()]
    risks = [[e(r), e(v["risk"]), e(v["priority"]), e(", ".join(v["acs"])), state(a["risk_status"][r])]
             for r, v in sorted(a["risks"].items())]
    defects = [[e(d["id"]), e(d["title"]), e(d["severity"]), e(d["priority"]), e(d["status"])] for d in a["open_defects"]]
    fails = "".join(f"<li>{e(c['class'])} › {e(c['name'])}</li>" for c in a["failures"]) or "<li>None</li>"
    sev = Counter(d["severity"] for d in a["open_defects"])
    total = sum(s["total"] for s in a["suites"].values())
    passed = sum(s[P] for s in a["suites"].values())
    acs_ok = sum(1 for s in a["ac_status"].values() if s == P)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Test report {e(version)}</title>
<style>
body{{margin:0;background:#0f1729;color:#e8ecf4;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1150px;margin:auto;padding:24px}} h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:28px 0 8px}}
.muted{{color:#93a0b8}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}}
.card{{background:#16213a;border:1px solid #25324f;border-radius:10px;padding:14px}} .card b{{display:block;font-size:26px}}
.decision{{border-left:6px solid {color};background:#16213a;padding:14px 18px;border-radius:0}}
.decision b{{color:{color};font-size:22px}}
table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{border-bottom:1px solid #25324f;padding:6px 8px;text-align:left;vertical-align:top}}
th{{color:#93a0b8;font-weight:600}} .passed{{color:#3fb68b}} .failed{{color:#ef6f5e;font-weight:600}} .not-run{{color:#93a0b8}}
a{{color:#5b9cf5}}
</style></head><body><main>
<h1>Test report · version {e(version)}</h1>
<div class="muted">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · <a href="/checklist">job checklist</a> ·
<a href="/docs/qa/traceability-matrix.md">traceability</a> · <a href="/docs/defects/README.md">defects</a></div>
<div class="cards">
 <div class="card"><span class="muted">Tests passed</span><b>{passed} / {total}</b></div>
 <div class="card"><span class="muted">Acceptance criteria green</span><b>{acs_ok} / {len(a['ac_status'])}</b></div>
 <div class="card"><span class="muted">Code coverage</span><b>{'—' if a['coverage'] is None else str(a['coverage']) + '%'}</b></div>
 <div class="card"><span class="muted">Risks with failures</span><b>{sum(1 for s in a['risk_status'].values() if s == F)}</b></div>
 <div class="card"><span class="muted">Open defects</span><b>{len(a['open_defects'])}</b>
   <span class="muted">{e(' · '.join(f'{k}: {v}' for k, v in sev.items()) or 'none')}</span></div>
</div>
<div class="decision">Recommendation: <b>{decision}</b><br>{e(reason)}</div>
<h2>Progress by suite</h2>{table(['Suite', 'Total', 'Passed', 'Failed', 'Skipped'], suites)}
<h2>Failed tests</h2><ul>{fails}</ul>
<h2>Acceptance criteria coverage</h2>{table(['Criterion', 'Description', 'Result'], acs)}
<h2>Risks</h2>{table(['Risk', 'Description', 'Priority', 'Criteria', 'Result'], risks)}
<h2>Open defects</h2>{table(['ID', 'Title', 'Severity', 'Priority', 'Status'], defects) if defects else '<p>None.</p>'}
<h2>Training defects</h2><p class="muted">They only exist with challenge mode on (QA_LAB_CHALLENGE=1). If any test linked to them failed, challenge mode was active.</p>
{table(['ID', 'Title', 'Severity', 'Criteria'], [[e(d['id']), e(d['title']), e(d['severity']), e(', '.join(d['acs']))] for d in a['training']])}
</main></body></html>"""


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "reports"
    version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("APP_VERSION", "?")
    a = analyse(folder)
    text = markdown(a, version)
    print(text)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "test-summary.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(a, version))
    decision, _ = recommendation(a)
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
