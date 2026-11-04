#!/usr/bin/env python3
"""
Lab Jenkins control (technical fix for DEF-008, corrected by DEF-014).

Runs INSIDE the Jenkins container (standard library only):
    python3 /tmp/jenkins_ctl.py pause    # disables the pipeline jobs (no new builds) and waits for running builds to finish
    python3 /tmp/jenkins_ctl.py resume   # enables the multibranch job again (and cancels any quiet down left behind)
    python3 /tmp/jenkins_ctl.py status

Why the job is disabled instead of using "quiet down" (DEF-014): in quiet down mode Jenkins also PAUSES
running Pipeline builds ("Pausing (Preparing for shutdown)"), so waiting for them to finish never ends.
A disabled job starts no new builds (not even from SCM polling) while running builds carry on normally.

Exit codes: 0 = OK, 1 = builds still running at the time limit, 2 = connection error,
3 = Jenkins is up but the pipeline job is not loaded (DEF-018: restart Jenkins once).
"""

import base64
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

URL = "http://localhost:8080"
JOB = "/job/qa-lab"                    # multibranch job (one job per branch, from GitHub)
LEGACY_JOB = "/job/qa-lab-pipeline"    # single-branch job used until the PR workflow: kept DISABLED (build history)
AUTH = "Basic " + base64.b64encode(b"admin:admin").decode()
WAIT_SECONDS = 900
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, method="GET"):
    req = urllib.request.Request(URL + path, method=method, headers={"Authorization": AUTH})
    if method == "POST":
        crumb = json.load(opener.open(urllib.request.Request(URL + "/crumbIssuer/api/json",
                                                             headers={"Authorization": AUTH}), timeout=15))
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
        if action in ("pause", "quiet-down"):
            call("/cancelQuietDown", "POST")          # never leave running builds paused (DEF-014)
            for job in (JOB, LEGACY_JOB):
                try:
                    call(job + "/disable", "POST")
                    print(f"Job {job} disabled: Jenkins will not start new builds from it.")
                except urllib.error.HTTPError as exc:
                    if exc.code not in (404, 405):    # 404 = the job does not exist (yet)
                        raise
            deadline = time.time() + WAIT_SECONDS
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
            try:
                call(JOB + "/api/json?tree=name")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    # DEF-018: Jenkins is up but the job created by configuration as code was not loaded
                    print(f"Job {JOB} not loaded by Jenkins (DEF-018): a restart is needed.")
                    return 3
                raise
            try:
                call(JOB + "/enable", "POST")
            except urllib.error.HTTPError as exc:
                if exc.code not in (404, 405):        # not disabled / nothing to enable
                    raise
            print("Job /job/qa-lab enabled: Jenkins accepts builds again.")
        else:
            info = call("/api/json?tree=quietingDown")
            job = call(JOB + "/api/json?tree=buildable")
            busy, names = running_builds()
            print(f"Job enabled: {job.get('buildable')} - quiet down: {info.get('quietingDown')} - running builds: {busy} {names}")
        return 0
    except OSError as exc:
        print(f"Error talking to Jenkins: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
