#!/usr/bin/env python3
"""Resolve what a Plasma Look-and-Feel package actually pulls in.

A global theme from store.kde.org ships configuration, not artwork: the visible parts are
KNewStuff dependencies listed in metadata.desktop. This asks the OCS API what each dependency is,
so an audit can be done on facts (type, author, version, download) instead of on the store page.

    python tools/visual/kns_audit.py <dir-with-lookandfeel-packages>

Writes kns_audit.json next to the working directory and prints one line per dependency.
Used for docs/PLASMA_THEME_AUDIT.md (run #29).
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "themes")

ids = []
for meta in ROOT.glob("*/metadata.desktop"):
    text = meta.read_text()
    m = re.search(r"X-KPackage-Dependencies=(.*)", text)
    for dep in m.group(1).split(","):
        kind, rest = dep.split("://")[1].split("/api.kde-look.org/")
        ids.append((meta.parent.name, kind.replace(".knsrc",""), rest.strip()))

seen = {}
for theme, kind, cid in ids:
    if cid in seen:
        seen[cid]["themes"].add(theme); continue
    raw = subprocess.run(["curl","-s","-m","25",f"https://api.kde-look.org/ocs/v1/content/data/{cid}?format=json"],capture_output=True,text=True).stdout
    try:
        d = json.loads(raw)["data"][0]
    except Exception:
        seen[cid] = {"themes":{theme},"kind":kind,"error":raw[:120]}; continue
    dls = []
    for i in range(1,7):
        name = d.get(f"downloadname{i}") or ""
        link = d.get(f"downloadlink{i}") or ""
        if link: dls.append((name, link, d.get(f"downloadsize{i}")))
    seen[cid] = {"themes":{theme},"kind":kind,"name":d.get("name"),"type":d.get("typename"),
                 "version":d.get("version"),"author":d.get("personid"),"license":d.get("license") or d.get("licensetype") or "",
                 "page":d.get("detailpage"),"downloads":dls}
Path("kns_audit.json").write_text(json.dumps(seen,indent=1,default=list))
for cid,v in seen.items():
    print(f"{cid} {v.get('kind'):14s} {str(v.get('type')):26s} {str(v.get('name'))[:34]:34s} v{v.get('version')} lic={v.get('license')!r} files={len(v.get('downloads',[]))} themes={sorted(v['themes'])}")
