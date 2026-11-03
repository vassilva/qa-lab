"""
Reads the repository's QA artifacts, shared by the test report and the traceability matrix:
acceptance criteria and scenarios (features/*.feature), risks (docs/qa/risk-matrix.md),
manual test cases (docs/qa/manual-test-cases.md), defects (docs/defects/DEF-*.md)
and test results (JUnit XML reports).
"""

import glob
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AC_RE = re.compile(r"AC-[A-Z]\d{2}")

PASSED, FAILED, SKIPPED, NOT_RUN = "passed", "failed", "skipped", "not run"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def features():
    """Returns (criteria, scenarios). Criterion: {id: {text, feature}}. Scenario: name, acs, tags, file, line."""
    criteria, scenarios = {}, []
    for path in sorted(glob.glob(os.path.join(ROOT, "features", "*.feature"))):
        feature_name, tags, in_criteria = "", [], False
        for n, line in enumerate(_read(path).splitlines(), 1):
            s = line.strip()
            if s.startswith("Feature:"):
                feature_name = s.split(":", 1)[1].strip()
            elif s.startswith("Acceptance criteria"):
                in_criteria = True
            elif in_criteria and re.match(r"AC-[A-Z]\d{2}\s", s):
                ac, text = s.split(None, 1)
                criteria[ac] = {"text": text.strip(), "feature": feature_name}
            elif s.startswith("@"):
                tags += s.split()
                in_criteria = False
            elif re.match(r"(Scenario|Scenario Outline):", s):
                in_criteria = False
                scenarios.append({
                    "name": s.split(":", 1)[1].strip(),
                    "acs": sorted({t[1:] for t in tags if AC_RE.fullmatch(t[1:])}),
                    "tags": tags,
                    "file": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                    "line": n,
                })
                tags = []
            elif s.startswith(("Background:", "Examples")):
                in_criteria, tags = False, [] if s.startswith("Background:") else tags
    return criteria, scenarios


def _table_rows(text, first_col_pattern):
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(first_col_pattern, cells[0]):
            rows.append(cells)
    return rows


def risks():
    """{R-xx: {risk, component, score, priority, acs}} from the risk matrix."""
    path = os.path.join(ROOT, "docs", "qa", "risk-matrix.md")
    out = {}
    for c in _table_rows(_read(path), r"R-\d{2}"):
        out[c[0]] = {"risk": c[1], "component": c[2], "score": c[5], "priority": c[6],
                     "acs": AC_RE.findall(c[7])}
    return out


def manual_cases():
    """{TC-Mxx: {title, acs}} from the summary table of the manual test cases."""
    path = os.path.join(ROOT, "docs", "qa", "manual-test-cases.md")
    return {c[0]: {"title": c[1], "acs": AC_RE.findall(c[2])} for c in _table_rows(_read(path), r"TC-M\d{2}")}


def defects():
    """List of defects with the fields of the header table of each DEF-NNN.md."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "docs", "defects", "DEF-*.md"))):
        text = _read(path)
        first = text.splitlines()[0]
        fields = {c[0]: c[1] for c in _table_rows(text, r"[A-Za-z ]+") if len(c) >= 2}
        out.append({
            "id": os.path.basename(path)[:-3],
            "title": first.split("·", 1)[1].strip() if "·" in first else first,
            "status": fields.get("Status", ""),
            "severity": fields.get("Severity", ""),
            "priority": fields.get("Priority", ""),
            "component": fields.get("Component", ""),
            "acs": AC_RE.findall(fields.get("Acceptance criterion", "")),
        })
    return out


def junit_results(folder):
    """List of test cases: suite (BDD/pytest), name, state (passed/failed/skipped)."""
    cases = []
    for path in sorted(glob.glob(os.path.join(folder, "**", "*.xml"), recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        suite = "BDD" if "behave" in path.replace(os.sep, "/") else "Component and API"
        for case in root.iter("testcase"):
            if case.find("skipped") is not None:
                state = SKIPPED
            elif case.find("failure") is not None or case.find("error") is not None:
                state = FAILED
            else:
                state = PASSED
            cases.append({"suite": suite, "class": case.get("classname", ""), "name": case.get("name", ""),
                          "state": state})
    return cases


def scenario_results(scenarios, cases):
    """Attaches the BDD result to each scenario (an outline passes only if every example passes)."""
    bdd = [c for c in cases if c["suite"] == "BDD"]
    for sc in scenarios:
        mine = [c for c in bdd if c["name"] == sc["name"] or c["name"].startswith(sc["name"] + " -- ")]
        if not mine:
            sc["result"] = NOT_RUN
        elif any(c["state"] == FAILED for c in mine):
            sc["result"] = FAILED
        elif all(c["state"] == SKIPPED for c in mine):
            sc["result"] = NOT_RUN
        else:
            sc["result"] = PASSED
    return scenarios


def combine(states):
    """Result of a group: failed if any failed, passed if all passed, otherwise not run."""
    states = set(states)
    return FAILED if FAILED in states else (PASSED if states == {PASSED} else NOT_RUN)
