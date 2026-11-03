#!/usr/bin/env python3
"""
Controlo do Jenkins do laboratorio (correcao tecnica do DEF-008).

Corre DENTRO do contentor do Jenkins (so usa a biblioteca padrao):
    python3 /tmp/jenkins_ctl.py quiet-down   # nao arranca builds novos; espera que os builds em curso terminem
    python3 /tmp/jenkins_ctl.py resume       # volta a aceitar builds
    python3 /tmp/jenkins_ctl.py status

Codigos de saida: 0 = OK, 1 = ainda ha builds em curso ao fim do tempo limite, 2 = erro de ligacao.
"""

import base64
import http.cookiejar
import json
import sys
import time
import urllib.request

URL = "http://localhost:8080"
AUTH = "Basic " + base64.b64encode(b"admin:admin").decode()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, method="GET"):
    req = urllib.request.Request(URL + path, method=method, headers={"Authorization": AUTH})
    if method == "POST":
        crumb = json.load(opener.open(urllib.request.Request(URL + "/crumbIssuer/api/json",
                                                             headers={"Authorization": AUTH})))
        req.add_header(crumb["crumbRequestField"], crumb["crumb"])
    with opener.open(req, timeout=15) as r:
        body = r.read()
    return json.loads(body) if body.strip().startswith(b"{") else {}


def running_builds():
    data = call("/computer/api/json?tree=busyExecutors,computer[executors[currentExecutable[fullDisplayName]]]")
    names = [e["currentExecutable"]["fullDisplayName"] for c in data.get("computer", [])
             for e in c.get("executors", []) if e.get("currentExecutable")]
    return data.get("busyExecutors", 0), names


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        if action == "quiet-down":
            call("/quietDown", "POST")
            print("Jenkins em pausa: nao vai arrancar builds novos.")
            deadline = time.time() + 600
            while True:
                busy, names = running_builds()
                if busy == 0:
                    print("Nenhum build em curso: pode atualizar as ferramentas.")
                    return 0
                if time.time() > deadline:
                    print(f"Ainda ha {busy} build(s) em curso: {', '.join(names)}")
                    print("Se um build esta a espera do go/no-go, aprova-o ou cancela-o no Jenkins e repete.")
                    return 1
                print(f"A aguardar que terminem {busy} build(s): {', '.join(names)}")
                time.sleep(10)
        elif action == "resume":
            call("/cancelQuietDown", "POST")
            print("Jenkins volta a aceitar builds.")
        else:
            info = call("/api/json?tree=quietingDown")
            busy, names = running_builds()
            print(f"Em pausa: {info.get('quietingDown')} - builds em curso: {busy} {names}")
        return 0
    except OSError as exc:
        print(f"Erro a falar com o Jenkins: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
