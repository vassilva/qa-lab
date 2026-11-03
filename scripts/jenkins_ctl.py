#!/usr/bin/env python3
"""
Lab Jenkins control (technical fix for DEF-008).

Runs INSIDE the Jenkins container (standard library only):
    python3 /tmp/jenkins_ctl.py quiet-down   # starts no new builds; waits for running builds to finish
    python3 /tmp/jenkins_ctl.py resume       # accepts builds again
    python3 /tmp/jenkins_ctl.py status

Exit codes: 0 = OK, 1 = builds still running at the time limit, 2 = connection error.
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
            print("Jenkins paused: it will not start new builds.")
            deadline = time.time() + 600
            while True:
                busy, names = running_builds()
                if busy == 0:
                    print("No builds running: the tools can be updated.")
                    return 0
                if time.time() > deadline:
                    print(f"Still {busy} build(s) running: {', '.join(names)}")
                    print("If a build is waiting for the go/no-go, approve or abort it in Jenkins and try again.")
                    return 1
                print(f"Waiting for {busy} build(s) to finish: {', '.join(names)}")
                time.sleep(10)
        elif action == "resume":
            call("/cancelQuietDown", "POST")
            print("Jenkins accepts builds again.")
        else:
            info = call("/api/json?tree=quietingDown")
            busy, names = running_builds()
            print(f"Paused: {info.get('quietingDown')} - running builds: {busy} {names}")
        return 0
    except OSError as exc:
        print(f"Error talking to Jenkins: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
