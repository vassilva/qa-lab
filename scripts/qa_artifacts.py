"""
Leitura dos artefactos de QA do repositório, partilhada pelo relatório e pela rastreabilidade:
critérios de aceitação e cenários (features/*.feature), riscos (docs/qa/matriz-de-risco.md),
casos manuais (docs/qa/casos-de-teste-manuais.md), defeitos (docs/defeitos/DEF-*.md)
e resultados de testes (relatórios JUnit XML).
"""

import glob
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AC_RE = re.compile(r"AC-[A-Z]\d{2}")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def features():
    """Devolve (critérios, cenários). Critério: {id: {texto, funcionalidade}}. Cenário: nome, ACs, tags, ficheiro, linha."""
    criteria, scenarios = {}, []
    for path in sorted(glob.glob(os.path.join(ROOT, "features", "*.feature"))):
        feature_name, tags, in_criteria = "", [], False
        for n, line in enumerate(_read(path).splitlines(), 1):
            s = line.strip()
            if s.startswith("Funcionalidade:"):
                feature_name = s.split(":", 1)[1].strip()
            elif s.startswith("Critérios de aceitação"):
                in_criteria = True
            elif in_criteria and re.match(r"AC-[A-Z]\d{2}\s", s):
                ac, text = s.split(None, 1)
                criteria[ac] = {"texto": text.strip(), "funcionalidade": feature_name}
            elif s.startswith("@"):
                tags += s.split()
                in_criteria = False
            elif re.match(r"(Cenário|Esquema do Cenário):", s):
                in_criteria = False
                scenarios.append({
                    "nome": s.split(":", 1)[1].strip(),
                    "acs": sorted({t[1:] for t in tags if AC_RE.fullmatch(t[1:])}),
                    "tags": tags,
                    "ficheiro": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                    "linha": n,
                })
                tags = []
            elif s.startswith(("Contexto:", "Exemplos")):
                in_criteria, tags = False, [] if s.startswith("Contexto:") else tags
    return criteria, scenarios


def _table_rows(text, first_col_pattern):
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(first_col_pattern, cells[0]):
            rows.append(cells)
    return rows


def risks():
    """{R-xx: {risco, prioridade, acs}} a partir da matriz de risco."""
    path = os.path.join(ROOT, "docs", "qa", "matriz-de-risco.md")
    out = {}
    for c in _table_rows(_read(path), r"R-\d{2}"):
        out[c[0]] = {"risco": c[1], "componente": c[2], "pontuacao": c[5], "prioridade": c[6],
                     "acs": AC_RE.findall(c[7])}
    return out


def manual_cases():
    """{TC-Mxx: {titulo, acs}} a partir da tabela inicial dos casos manuais."""
    path = os.path.join(ROOT, "docs", "qa", "casos-de-teste-manuais.md")
    return {c[0]: {"titulo": c[1], "acs": AC_RE.findall(c[2])} for c in _table_rows(_read(path), r"TC-M\d{2}")}


def defects():
    """Lista de defeitos com os campos da tabela de cabeçalho de cada DEF-NNN.md."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "docs", "defeitos", "DEF-*.md"))):
        text = _read(path)
        first = text.splitlines()[0]
        fields = {c[0]: c[1] for c in _table_rows(text, r"[A-Za-zÀ-ú ]+") if len(c) >= 2}
        out.append({
            "id": os.path.basename(path)[:-3],
            "titulo": first.split("·", 1)[1].strip() if "·" in first else first,
            "estado": fields.get("Estado", ""),
            "severidade": fields.get("Severidade", ""),
            "prioridade": fields.get("Prioridade", ""),
            "componente": fields.get("Componente", ""),
            "acs": AC_RE.findall(fields.get("Critério de aceitação", "")),
        })
    return out


def junit_results(folder):
    """Lista de casos de teste: suite (BDD/pytest), nome, estado (passou/falhou/ignorado)."""
    cases = []
    for path in sorted(glob.glob(os.path.join(folder, "**", "*.xml"), recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        suite = "BDD" if "behave" in path.replace(os.sep, "/") else "Componentes e API"
        for case in root.iter("testcase"):
            if case.find("skipped") is not None:
                state = "ignorado"
            elif case.find("failure") is not None or case.find("error") is not None:
                state = "falhou"
            else:
                state = "passou"
            cases.append({"suite": suite, "classe": case.get("classname", ""), "nome": case.get("name", ""),
                          "estado": state})
    return cases


def scenario_results(scenarios, cases):
    """Associa o resultado BDD a cada cenário (um esquema passa só se todos os exemplos passarem)."""
    bdd = [c for c in cases if c["suite"] == "BDD"]
    for sc in scenarios:
        mine = [c for c in bdd if c["nome"] == sc["nome"] or c["nome"].startswith(sc["nome"] + " -- ")]
        if not mine:
            sc["resultado"] = "não executado"
        elif any(c["estado"] == "falhou" for c in mine):
            sc["resultado"] = "falhou"
        elif all(c["estado"] == "ignorado" for c in mine):
            sc["resultado"] = "não executado"
        else:
            sc["resultado"] = "passou"
    return scenarios
