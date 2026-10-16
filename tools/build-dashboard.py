#!/usr/bin/env python3
"""Builds the public dashboard from the internal Bulletin Paseo dashboard.

Usage: tools/build-dashboard.py <bulletin-paseo-dashboard.json> > grafana/dashboards/bulletin-collators.json

The source is dashboards/bulletin-paseo-dashboard.json in the private
paritytech/bulletin-grafana-dashboards repo. The script:
- removes the rows that read Parity infrastructure (the kubo IPFS gateway),
- replaces the internal `node` label with `operator` (set in prometheus/targets),
- adds a "Collators" row and bitswap traffic panels.
"""
import json
import re
import sys

DROP_ROWS = {"IPFS gateway (kubo)"}
DS = {"type": "prometheus", "uid": "${datasource}"}
# Counters that the node registers only after the first event. Without
# events the panel shows this text instead of "No data".
NO_VALUE = {"HOP errors by method/reason": "No errors"}


def to_operator(text):
    text = text.replace("$node", "$operator")
    return re.sub(r"\bnode\b", "operator", text)


def target(expr, legend, ref="A", fmt=None, instant=False):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if fmt:
        t["format"] = fmt
    if instant:
        t["instant"] = True
        t["range"] = False
    return t


def panel(kind, title, targets, x, y, w, h, unit=None, description=None, **extra):
    p = {
        "type": kind,
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {},
    }
    if unit:
        p["fieldConfig"]["defaults"]["unit"] = unit
    if description:
        p["description"] = description
    p.update(extra)
    return p


def row(title, y):
    return {"type": "row", "title": title, "collapsed": False, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def overview_panels():
    return [
        row("Collators", 0),
        panel("stat", "Collators reporting", [target('count(up{job="bulletin-collators", operator=~"$operator"} == 1) or vector(0)', "reporting", instant=True)],
              0, 1, 4, 6, description="Collators whose metrics endpoint answered the last scrape."),
        panel("state-timeline", "Metrics endpoint reachable", [target('max by (operator) (up{job="bulletin-collators", operator=~"$operator"})', "{{operator}}")],
              4, 1, 10, 6, description="1 = the last scrape succeeded. A gap means the operator's endpoint was down or unreachable.",
              fieldConfig={"defaults": {"mappings": [{"type": "value", "options": {"0": {"text": "down", "color": "red"}, "1": {"text": "up", "color": "green"}}}], "color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}}, "overrides": []}),
        panel("table", "Node versions", [target('max by (operator, version) (substrate_build_info{job="bulletin-collators", operator=~"$operator"})', "", fmt="table", instant=True)],
              14, 1, 10, 6, description="Node version reported by each collator. Bitswap metrics need polkadot-sdk stable2609 or newer.",
              transformations=[{"id": "organize", "options": {"excludeByName": {"Time": True, "Value": True}}}]),
    ]


def bitswap_panels(y):
    return [
        panel("timeseries", "Bitswap data served", [target('sum by (operator) (rate(substrate_sub_libp2p_bitswap_response_bytes_total{chain=~"$chain", operator=~"$operator"}[5m]))', "{{operator}}")],
              0, y, 12, 8, unit="Bps", description="Bytes sent to IPFS clients over bitswap."),
        panel("timeseries", "Bitswap wantlist entries by outcome", [target('sum by (outcome) (rate(substrate_sub_libp2p_bitswap_entries_total{chain=~"$chain", operator=~"$operator"}[5m]))', "{{outcome}}")],
              12, y, 12, 8, unit="reqps", description="Requested blocks per second, split by outcome (block sent, have, dont_have)."),
    ]


def main(src_path):
    src = json.load(open(src_path))
    panels, current_row, y_shift = [], None, 7
    bitswap_inserted = False
    for p in src["panels"]:
        if p["type"] == "row":
            current_row = p["title"]
        if current_row in DROP_ROWS:
            continue
        p = json.loads(to_operator(json.dumps(p)))
        p.pop("id", None)
        if p.get("title") in NO_VALUE:
            p.setdefault("fieldConfig", {}).setdefault("defaults", {})["noValue"] = NO_VALUE[p["title"]]
        p["gridPos"]["y"] += y_shift
        panels.append(p)
        if p["type"] == "row" and p["title"] == "Bitswap" and not bitswap_inserted:
            extra = bitswap_panels(p["gridPos"]["y"] + 1)
            panels.extend(extra)
            y_shift += 8
            bitswap_inserted = True

    for i, p in enumerate(overview_panels() + panels, start=1):
        p["id"] = i

    variables = [
        {"name": "datasource", "type": "datasource", "query": "prometheus", "hide": 2, "current": {"text": "Prometheus", "value": "prometheus"}},
        {"name": "chain", "label": "Chain", "type": "query", "datasource": DS, "refresh": 2,
         "query": {"query": 'label_values(substrate_block_height{job="bulletin-collators"}, chain)', "refId": "chain"},
         "definition": 'label_values(substrate_block_height{job="bulletin-collators"}, chain)',
         "current": {"text": "bulletin-polkadot", "value": "bulletin-polkadot"}},
        {"name": "operator", "label": "Operator", "type": "query", "datasource": DS, "refresh": 2, "multi": True, "includeAll": True,
         "allValue": ".*", "current": {"text": "All", "value": "$__all"},
         "query": {"query": 'label_values(up{job="bulletin-collators"}, operator)', "refId": "operator"},
         "definition": 'label_values(up{job="bulletin-collators"}, operator)'},
    ]

    out = {
        "uid": "bulletin-collators",
        "title": "Bulletin Collators",
        "description": "Metrics shared voluntarily by Bulletin collator operators.",
        "tags": ["bulletin"],
        "timezone": "utc",
        "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "schemaVersion": src.get("schemaVersion", 39),
        "editable": False,
        "graphTooltip": 1,
        "templating": {"list": variables},
        "annotations": {"list": []},
        "panels": overview_panels() + panels,
    }
    for i, p in enumerate(out["panels"], start=1):
        p["id"] = i
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
