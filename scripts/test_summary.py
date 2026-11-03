#!/usr/bin/env python3
"""
Relatório de testes para a decisão go/no-go.

Lê os relatórios JUnit XML de uma pasta (pytest e behave) e os artefactos de QA do repositório, e escreve:
  <pasta>/resumo-testes.md   resumo em texto (também mostrado no ecrã / no log do Jenkins)
  <pasta>/index.html         relatório: progresso, cobertura dos critérios de aceitação, riscos, defeitos

Uso: python3 scripts/test_summary.py [pasta] [versão]
Sai com código 1 se algum teste falhou ou se não houver resultados.
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

OPEN_STATES = ("Novo", "Em análise", "Confirmado", "Em correção", "Corrigido", "Em reteste", "Reaberto", "Aberto")


def analyse(folder):
    cases = qa.junit_results(folder)
    criteria, scenarios = qa.features()
    qa.scenario_results(scenarios, cases)
    risks, defects = qa.risks(), qa.defects()

    suites = {}
    for c in cases:
        s = suites.setdefault(c["suite"], Counter())
        s["total"] += 1
        s[c["estado"]] += 1
    ac_status = {}
    for ac in criteria:
        states = {s["resultado"] for s in scenarios if ac in s["acs"]}
        ac_status[ac] = "falhou" if "falhou" in states else ("passou" if states == {"passou"} else "não executado")
    risk_status = {}
    for rid, r in risks.items():
        states = {ac_status.get(a, "não executado") for a in r["acs"]}
        risk_status[rid] = "falhou" if "falhou" in states else ("passou" if states == {"passou"} else "não executado")
    coverage = None
    for path in glob.glob(os.path.join(folder, "**", "coverage.xml"), recursive=True):
        try:
            coverage = round(100 * float(ET.parse(path).getroot().get("line-rate", 0)), 1)
        except (ET.ParseError, ValueError):
            pass
    open_defects = [d for d in defects if d["estado"].startswith(OPEN_STATES) and "modo desafio" not in d["estado"]]
    training = [d for d in defects if "modo desafio" in d["estado"]]
    failures = [c for c in cases if c["estado"] == "falhou"]
    return dict(cases=cases, suites=suites, criteria=criteria, ac_status=ac_status, risks=risks,
                risk_status=risk_status, coverage=coverage, open_defects=open_defects, training=training, failures=failures)


def recommendation(a):
    if not a["cases"]:
        return "SEM RESULTADOS", "Não foram encontrados resultados de testes."
    critical_fail = [r for r, s in a["risk_status"].items() if s == "falhou" and a["risks"][r]["prioridade"] in ("Crítica", "Alta")]
    if a["failures"] or critical_fail:
        return "NO-GO", f"{len(a['failures'])} teste(s) falhado(s); {len(critical_fail)} risco(s) crítico(s)/alto(s) com falhas."
    return "GO", "Todos os testes automáticos passaram. Confirmar o checklist de release antes de aprovar."


def markdown(a, version):
    decision, reason = recommendation(a)
    lines = [f"# Resumo de testes · versão {version}", "",
             "| Suite | Total | Passados | Falhados | Ignorados |", "| --- | ---: | ---: | ---: | ---: |"]
    tot = Counter()
    for name, s in sorted(a["suites"].items()):
        lines.append(f"| {name} | {s['total']} | {s['passou']} | {s['falhou']} | {s['ignorado']} |")
        tot.update(s)
    lines.append(f"| **Total** | **{tot['total']}** | **{tot['passou']}** | **{tot['falhou']}** | **{tot['ignorado']}** |")
    acs = Counter(a["ac_status"].values())
    if a["coverage"] is not None:
        lines += ["", f"Cobertura de código (testes de componente e API): {a['coverage']}%"]
    lines += ["", f"Critérios de aceitação: {acs['passou']} passaram · {acs['falhou']} falharam · "
                  f"{acs['não executado']} não executados (de {len(a['ac_status'])})."]
    if a["failures"]:
        lines += ["", "## Testes falhados"] + [f"- {c['classe']} › {c['nome']}" for c in a["failures"]]
    lines += ["", f"**Recomendação: {decision}** · {reason}"]
    return "\n".join(lines) + "\n"


def page(a, version):
    decision, reason = recommendation(a)
    e = html.escape
    color = {"GO": "#2f9e6e", "NO-GO": "#d9534f"}.get(decision, "#b07a1e")
    badge = {"passou": "✓ passou", "falhou": "✗ falhou", "não executado": "— não executado"}

    def table(head, rows):
        return ("<table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr></thead><tbody>" +
                "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")

    suites = [[e(n), s["total"], s["passou"], s["falhou"], s["ignorado"]] for n, s in sorted(a["suites"].items())]
    acs = [[f"<b>{e(ac)}</b>", e(a["criteria"][ac]["texto"]), f'<span class="{st.replace(" ", "-")}">{badge[st]}</span>']
           for ac, st in a["ac_status"].items()]
    risks = [[e(r), e(v["risco"]), e(v["prioridade"]), e(", ".join(v["acs"])),
              f'<span class="{a["risk_status"][r].replace(" ", "-")}">{badge[a["risk_status"][r]]}</span>']
             for r, v in sorted(a["risks"].items())]
    defects = [[e(d["id"]), e(d["titulo"]), e(d["severidade"]), e(d["prioridade"]), e(d["estado"])] for d in a["open_defects"]]
    fails = "".join(f"<li>{e(c['classe'])} › {e(c['nome'])}</li>" for c in a["failures"]) or "<li>Nenhum</li>"
    sev = Counter(d["severidade"] for d in a["open_defects"])
    total = sum(s["total"] for s in a["suites"].values())
    passed = sum(s["passou"] for s in a["suites"].values())
    acs_ok = sum(1 for s in a["ac_status"].values() if s == "passou")

    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Relatório de testes {e(version)}</title>
<style>
body{{margin:0;background:#0f1729;color:#e8ecf4;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1150px;margin:auto;padding:24px}} h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:28px 0 8px}}
.muted{{color:#93a0b8}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}}
.card{{background:#16213a;border:1px solid #25324f;border-radius:10px;padding:14px}} .card b{{display:block;font-size:26px}}
.decision{{border-left:6px solid {color};background:#16213a;padding:14px 18px;border-radius:0}}
.decision b{{color:{color};font-size:22px}}
table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{border-bottom:1px solid #25324f;padding:6px 8px;text-align:left;vertical-align:top}}
th{{color:#93a0b8;font-weight:600}} .passou{{color:#3fb68b}} .falhou{{color:#ef6f5e;font-weight:600}} .não-executado{{color:#93a0b8}}
a{{color:#5b9cf5}}
</style></head><body><main>
<h1>Relatório de testes · versão {e(version)}</h1>
<div class="muted">Gerado em {datetime.now().strftime('%Y-%m-%d %H:%M')} · <a href="/checklist">checklist da vaga</a> ·
<a href="/docs/qa/matriz-de-rastreabilidade.md">rastreabilidade</a> · <a href="/docs/defeitos/README.md">defeitos</a></div>
<div class="cards">
 <div class="card"><span class="muted">Testes passados</span><b>{passed} / {total}</b></div>
 <div class="card"><span class="muted">Critérios de aceitação verdes</span><b>{acs_ok} / {len(a['ac_status'])}</b></div>
 <div class="card"><span class="muted">Cobertura de código</span><b>{'—' if a['coverage'] is None else str(a['coverage']) + '%'}</b></div>
 <div class="card"><span class="muted">Riscos com falhas</span><b>{sum(1 for s in a['risk_status'].values() if s == 'falhou')}</b></div>
 <div class="card"><span class="muted">Defeitos abertos</span><b>{len(a['open_defects'])}</b>
   <span class="muted">{e(' · '.join(f'{k}: {v}' for k, v in sev.items()) or 'nenhum')}</span></div>
</div>
<div class="decision">Recomendação: <b>{decision}</b><br>{e(reason)}</div>
<h2>Progresso por suite</h2>{table(['Suite', 'Total', 'Passados', 'Falhados', 'Ignorados'], suites)}
<h2>Testes falhados</h2><ul>{fails}</ul>
<h2>Cobertura dos critérios de aceitação</h2>{table(['Critério', 'Descrição', 'Resultado'], acs)}
<h2>Riscos</h2>{table(['Risco', 'Descrição', 'Prioridade', 'Critérios', 'Resultado'], risks)}
<h2>Defeitos abertos</h2>{table(['ID', 'Título', 'Severidade', 'Prioridade', 'Estado'], defects) if defects else '<p>Nenhum.</p>'}
<h2>Defeitos de treino</h2><p class="muted">Só existem com o modo desafio ligado (QA_LAB_CHALLENGE=1). Se algum dos testes ligados a eles falhou, o modo desafio estava ativo.</p>
{table(['ID', 'Título', 'Severidade', 'Critérios'], [[e(d['id']), e(d['titulo']), e(d['severidade']), e(', '.join(d['acs']))] for d in a['training']])}
</main></body></html>"""


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "reports"
    version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("APP_VERSION", "?")
    a = analyse(folder)
    text = markdown(a, version)
    print(text)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "resumo-testes.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(a, version))
    decision, _ = recommendation(a)
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
