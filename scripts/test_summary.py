#!/usr/bin/env python3
"""
Resumo dos resultados de testes para a decisão go/no-go.

Lê todos os relatórios JUnit XML de uma pasta (pytest e behave), mostra o resumo no ecrã
e escreve-o em <pasta>/resumo-testes.md.

Uso: python3 scripts/test_summary.py [pasta] [versão]
Sai com código 1 se algum teste falhou.
"""

import glob
import os
import sys
import xml.etree.ElementTree as ET


def collect(folder):
    suites = {}
    failures = []
    for path in sorted(glob.glob(os.path.join(folder, "**", "*.xml"), recursive=True)):
        root = ET.parse(path).getroot()
        for suite in ([root] if root.tag == "testsuite" else root.iter("testsuite")):
            group = os.path.relpath(os.path.dirname(path), folder).split(os.sep)[0]
            name = "BDD" if "behave" in path else "Componentes e API (pytest)"
            key = f"{name} · {group}" if group not in (".", "") else name
            s = suites.setdefault(key, {"total": 0, "falhados": 0, "ignorados": 0})
            for case in suite.iter("testcase"):
                s["total"] += 1
                if case.find("skipped") is not None:
                    s["ignorados"] += 1
                elif case.find("failure") is not None or case.find("error") is not None:
                    s["falhados"] += 1
                    failures.append(f"{case.get('classname', '')} › {case.get('name', '')}")
    return suites, failures


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "reports"
    version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("APP_VERSION", "?")
    suites, failures = collect(folder)

    lines = [f"# Resumo de testes · versão {version}", "",
             "| Suite | Total | Passados | Falhados | Ignorados |", "| --- | ---: | ---: | ---: | ---: |"]
    totals = {"total": 0, "falhados": 0, "ignorados": 0}
    for name, s in suites.items():
        passed = s["total"] - s["falhados"] - s["ignorados"]
        lines.append(f"| {name} | {s['total']} | {passed} | {s['falhados']} | {s['ignorados']} |")
        for k in totals:
            totals[k] += s[k]
    passed = totals["total"] - totals["falhados"] - totals["ignorados"]
    lines.append(f"| **Total** | **{totals['total']}** | **{passed}** | **{totals['falhados']}** | **{totals['ignorados']}** |")
    lines.append("")
    if failures:
        lines.append("## Testes falhados")
        lines += [f"- {f}" for f in failures]
        lines.append("")
        lines.append("**Recomendação: NO-GO** até os defeitos serem analisados.")
    elif totals["total"] == 0:
        lines.append("**Atenção:** não foram encontrados resultados de testes.")
    else:
        lines.append("**Recomendação: GO** do ponto de vista dos testes automáticos "
                     "(confirmar o checklist de release).")

    text = "\n".join(lines) + "\n"
    print(text)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "resumo-testes.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return 1 if failures or totals["total"] == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
