#!/usr/bin/env python3
"""ARB guardrail: checks ADRs and design manifests against governance/principles.yaml.

Usage:
  python tools/arb_guardrail.py                         # lint adr/*.md, check designs/*.yaml
  python tools/arb_guardrail.py --expect-fail FILE ...  # pass only if FILE breaks every rule R1-R8

Exit code 1 means at least one violation, so CI blocks the merge.
"""
import argparse
import glob
import re
import sys

import yaml

PRINCIPLES = yaml.safe_load(open("governance/principles.yaml", encoding="utf-8"))
RULE_TO_PRINCIPLE = {r.split("-")[0]: pid for pid, p in PRINCIPLES["principles"].items() for r in p["rules"]}
ADR_SECTIONS = ["## Context", "## Options", "## Decision", "## Consequences"]
AI_TYPES = {"model", "llm", "agent", "recommender"}


def lint_adr(path):
    text = open(path, encoding="utf-8").read()
    errors = [f"missing section '{s}'" for s in ADR_SECTIONS if s not in text]
    if not re.search(r"\*\*Status:\*\*\s*(Proposed|Accepted|Superseded|Deprecated)", text):
        errors.append("missing or invalid **Status:**")
    m = re.search(r"\*\*Principles:\*\*\s*(.+)", text)
    if not m:
        errors.append("missing **Principles:** line")
    else:
        cited = re.findall(r"P\d+", m.group(1))
        unknown = [p for p in cited if p not in PRINCIPLES["principles"]]
        if not cited or unknown:
            errors.append(f"Principles line must cite known IDs, got {cited or m.group(1)!r}")
    return errors


def check_design(d):
    """Return a list of (rule, message) violations for one design manifest."""
    comps = {c["id"]: c for c in d.get("components", [])}
    out = []
    for f in d.get("flows", []):
        src, dst = comps.get(f["from"], {}), comps.get(f["to"], {})
        if dst.get("external") and f.get("pii") and not f.get("redacted"):
            # External LLMs never get raw PII; other processors need a lawful basis and a DPA.
            if dst.get("type") == "llm":
                out.append(("R1", f"PII flows {f['from']} -> external LLM {f['to']} without redaction"))
            elif not (f.get("lawful_basis") and f.get("processor_dpa")):
                out.append(("R1", f"PII flows {f['from']} -> external {f['to']} without redaction "
                                  "or lawful_basis + processor_dpa"))
        if src.get("type") == "operational_db" and dst.get("type") != "cdc" and f["to"] != src.get("owner"):
            out.append(("R7", f"{f['to']} reads the operational DB directly; use CDC -> Kafka"))
    for cid, c in comps.items():
        needs_region = c.get("type") in {"store", "llm", "operational_db"} or c.get("external")
        if needs_region and c.get("region") not in PRINCIPLES["allowed_regions"]:
            out.append(("R2", f"{cid} region {c.get('region')!r} not in allowed_regions"))
        if c.get("sends_to_customer") and not c.get("consent_check"):
            out.append(("R3", f"{cid} messages customers without a consent/opt-out check"))
        if c.get("generates_content") and c.get("customer_facing") and not (
                c.get("human_review") or c.get("approved_templates")):
            out.append(("R4", f"{cid} shows generated content with no human review or approved templates"))
        if c.get("mode") in {"realtime", "stream"} and not (c.get("justification") and c.get("latency_budget_ms")):
            out.append(("R5", f"{cid} is {c['mode']} but lacks justification and latency_budget_ms"))
        if c.get("type") in AI_TYPES:
            missing = [k for k in ("offline", "online_kpi", "kill_switch") if not (c.get("eval") or {}).get(k)]
            if missing:
                out.append(("R6", f"{cid} eval is missing {missing}"))
            if c.get("on_user_path") and not c.get("fallback"):
                out.append(("R8", f"{cid} is on a user path with no fallback"))
    return out


def report(label, violations):
    for rule, msg in violations:
        print(f"  FAIL {rule} ({RULE_TO_PRINCIPLE.get(rule, '?')}): {msg}")
    print(f"{'FAIL' if violations else 'PASS'} {label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-fail", nargs="+", metavar="FILE")
    args = ap.parse_args()

    if args.expect_fail:
        ok = True
        for path in args.expect_fail:
            fired = {r for r, _ in check_design(yaml.safe_load(open(path, encoding="utf-8")))}
            missed = sorted(set(RULE_TO_PRINCIPLE) - fired)
            print(f"{'PASS' if not missed else 'FAIL'} {path} triggers rules {sorted(fired)}"
                  + (f", missed {missed}" if missed else ""))
            ok &= not missed
        return 0 if ok else 1

    failed = False
    for path in sorted(glob.glob("adr/*.md")):
        errs = lint_adr(path)
        report(path, [("ADR", e) for e in errs])
        failed |= bool(errs)
    for path in sorted(glob.glob("designs/*.yaml")):
        v = check_design(yaml.safe_load(open(path, encoding="utf-8")))
        report(path, v)
        failed |= bool(v)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
