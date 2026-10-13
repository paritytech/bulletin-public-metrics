#!/usr/bin/env python3
"""Runs every panel query of the dashboard through Grafana as an anonymous
visitor and prints whether it returns data.

Usage: tools/check-dashboard.py [grafana_url]   (default http://localhost:8080)
"""
import json
import pathlib
import sys
import time
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
DASH = pathlib.Path(__file__).parent.parent / "grafana/dashboards/bulletin-collators.json"


def get(path):
    return json.load(urllib.request.urlopen(URL + path, timeout=10))


def query(expr, instant):
    now = int(time.time() * 1000)
    body = {"from": str(now - 3600_000), "to": str(now), "queries": [
        {"refId": "A", "datasource": {"type": "prometheus", "uid": "prometheus"}, "expr": expr,
         "instant": instant, "range": not instant, "intervalMs": 30000, "maxDataPoints": 200}]}
    req = urllib.request.Request(URL + "/api/ds/query", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=20))["results"]["A"]
    if "error" in res:
        return "ERROR " + res["error"][:80]
    series = [f for f in res.get("frames", []) if f["data"]["values"] and f["data"]["values"][0]]
    return f"{len(series)} series" if series else "no data"


chain = get("/api/datasources/proxy/uid/prometheus/api/v1/label/chain/values")["data"]
subs = {"$chain": "|".join(chain), "$operator": ".*", "$__rate_interval": "2m", "$__range": "1h"}
print(f"anonymous home page: {get('/api/dashboards/home').get('redirectUri')}")
failed = 0
for p in json.load(open(DASH))["panels"]:
    if p["type"] == "row":
        print(f"\n== {p['title']}")
        continue
    results = []
    for t in p.get("targets", []):
        expr = t["expr"]
        for k, v in subs.items():
            expr = expr.replace(k, v)
        results.append(query(expr, t.get("instant", False)))
    ok = all(r.endswith("series") for r in results)
    failed += not ok
    print(f"  {'OK ' if ok else '-- '} {p['title']}: {', '.join(results)}")
print(f"\n{failed} panels without data")
