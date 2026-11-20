"""mirror.py - keep a byte-exact copy of the inok.info app export (manifest.json + its files) for the app's fallback (InokApp ruling A-144).

Run by .github/workflows/mirror.yml every 6 hours. Rules:
- the site's manifest.json is published BYTE FOR BYTE, its files only when every sha256 / byte count matches the manifest;
- an export OLDER than the published one is never published; a failed fetch leaves the last good copy;
- status.json says when the site was last checked and with what result (written on a change of export or state, else weekly -
  that weekly commit keeps the scheduled workflow alive: GitHub stops schedules of a repository without activity for 60 days).
Exit 1 only on an integrity failure (a wrong sha256 / size from the site) - that one deserves the e-mail of a red run.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

BASE = "https://inok.info/api/app/v1/export/"
KEY = "eb741a6e64315c8aff6281ad13c21378"  # the app's PUBLIC key (InokApp ref/REF_app_api_contract.md section 1) - not a secret
UA = "InokApp-mirror/1.0 (+https://github.com/losjakov/inok-app-data)"
OUT = "export"
STATUS = "status.json"


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def get(name):
    req = urllib.request.Request(BASE + name, headers={"X-Inok-App": KEY, "User-Agent": UA, "Accept": "application/json, application/gzip"})
    with urllib.request.urlopen(req, timeout=90) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read()
    if name.endswith(".json") and not ctype.startswith("application/json"):
        raise ValueError("not JSON (" + ctype + ") - the hoster's page?")
    return body


def load(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def save_status(state, note, version, changed):
    old = {}
    raw = load(STATUS)
    if raw:
        try:
            old = json.loads(raw.decode("utf-8"))
        except ValueError:
            old = {}
    t = now()
    last = old.get("written_at")
    stale = True
    if last:
        try:
            stale = (t - datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))).days >= 7
        except ValueError:
            stale = True
    if not (changed or stale or old.get("state") != state):
        print("status unchanged (" + state + ")")
        return
    doc = {"written_at": t.isoformat().replace("+00:00", "Z"), "state": state, "note": note, "export_version": version,
           "source": BASE + "manifest.json"}
    write(STATUS, (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("status written: " + state)


def main():
    os.makedirs(OUT, exist_ok=True)
    cur_raw = load(os.path.join(OUT, "manifest.json"))
    cur = json.loads(cur_raw.decode("utf-8")) if cur_raw else {}
    cur_ver = cur.get("export_version", "")
    try:
        man_raw = get("manifest.json")
        man = json.loads(man_raw.decode("utf-8"))
        files = man["files"]
        ver = man["export_version"]
        assert man.get("contract_version") == 1, "contract_version"
        assert isinstance(files, list) and files, "files"
    except Exception as e:  # the site down / busy / not JSON: keep the last good copy
        save_status("site_unreachable", str(e)[:200], cur_ver, False)
        return 0
    if cur_ver and ver < cur_ver:
        save_status("older_refused", "the site's export " + ver + " is older than the published " + cur_ver, cur_ver, False)
        return 0
    blobs = {}
    for f in files:
        name = f["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            print("BAD FILE NAME " + name)
            return 1
        old = load(os.path.join(OUT, name))
        if ver == cur_ver and old is not None and hashlib.sha256(old).hexdigest() == f["sha256"]:
            continue
        try:
            data = get(name)
        except Exception as e:
            save_status("site_unreachable", name + ": " + str(e)[:180], cur_ver, False)
            return 0
        if hashlib.sha256(data).hexdigest() != f["sha256"] or len(data) != int(f["bytes"]):
            print("INTEGRITY FAILURE " + name + ": sha256 / size differ from the manifest - nothing published")
            save_status("integrity_failure", name, cur_ver, False)
            return 1
        blobs[name] = data
    changed = bool(blobs) or man_raw != cur_raw
    for name, data in blobs.items():
        write(os.path.join(OUT, name), data)
    if changed:
        write(os.path.join(OUT, "manifest.json"), man_raw)
    save_status("ok", "published " + ver if changed else "unchanged " + ver, ver, changed)
    with open(".msg", "w", encoding="utf-8") as m:
        m.write(("export " + ver) if changed else "status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
