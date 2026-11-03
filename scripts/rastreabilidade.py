#!/usr/bin/env python3
"""
Gera a matriz de rastreabilidade a partir dos artefactos do repositório:
    critério de aceitação → riscos → cenários BDD → casos manuais → defeitos (→ último resultado, se houver relatórios)

Uso: python3 scripts/rastreabilidade.py [pasta-de-relatorios]   (escreve docs/qa/matriz-de-rastreabilidade.md)
Assim a matriz nunca fica desatualizada: muda um cenário, regenera-se a matriz.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_artifacts as qa  # noqa: E402

OUT = os.path.join(qa.ROOT, "docs", "qa", "matriz-de-rastreabilidade.md")
ICON = {"passou": "✓ passou", "falhou": "✗ falhou", "não executado": "— não executado"}


def build(reports=None):
    criteria, scenarios = qa.features()
    risks, manual, defects = qa.risks(), qa.manual_cases(), qa.defects()
    has_results = bool(reports and os.path.isdir(reports))
    if has_results:
        qa.scenario_results(scenarios, qa.junit_results(reports))

    lines = [
        "# Matriz de rastreabilidade · QA Lab", "",
        f"Gerada automaticamente por `scripts/rastreabilidade.py` em {date.today().isoformat()}. Não editar à mão.", "",
        "| Critério de aceitação | Riscos | Cenários BDD | Casos manuais | Defeitos" + (" | Último resultado |" if has_results else " |"),
        "| --- | --- | --- | --- | ---" + (" | --- |" if has_results else " |"),
    ]
    uncovered = []
    for ac in criteria:                      # pela ordem das funcionalidades (validação → execução → liquidação)
        scs = [s for s in scenarios if ac in s["acs"]]
        if not scs:
            uncovered.append(ac)
        r = ", ".join(f"{rid} ({risks[rid]['prioridade']})" for rid in sorted(risks) if ac in risks[rid]["acs"]) or "—"
        sc_txt = "<br>".join(f"{s['nome']} (`{s['ficheiro']}:{s['linha']}`)" for s in scs) or "**sem cenário**"
        tc = ", ".join(t for t in sorted(manual) if ac in manual[t]["acs"]) or "—"
        df = ", ".join(f"{d['id']} ({d['estado']})" for d in defects if ac in d["acs"]) or "—"
        row = f"| **{ac}** {criteria[ac]['texto']} | {r} | {sc_txt} | {tc} | {df}"
        if has_results:
            states = {s.get("resultado", "não executado") for s in scs}
            res = "falhou" if "falhou" in states else ("passou" if states == {"passou"} else "não executado")
            row += f" | {ICON[res]}"
        lines.append(row + " |")

    automated = len(criteria) - len(uncovered)
    lines += [
        "",
        "## Cobertura",
        "",
        f"- Critérios de aceitação: **{len(criteria)}**, com cenário automatizado: **{automated}** "
        f"({round(100 * automated / max(len(criteria), 1))}%).",
        f"- Riscos de negócio cobertos por critérios com cenário: **{sum(1 for r in risks.values() if any(a not in uncovered for a in r['acs']))} de {len(risks)}**.",
        f"- Casos manuais: **{len(manual)}** · Defeitos registados: **{len(defects)}**.",
    ]
    if uncovered:
        lines.append(f"- Critérios sem cenário automatizado: {', '.join(uncovered)}.")
    return "\n".join(lines) + "\n"


def main():
    text = build(sys.argv[1] if len(sys.argv) > 1 else None)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Matriz escrita em {os.path.relpath(OUT, qa.ROOT)}")


if __name__ == "__main__":
    main()
