# ai-architecture-portfolio

Deliverables from the **AI Architecture Design** course. Case study: *Marketing Automation System with AI & Agents*.

| Folder | Contents |
|---|---|
| [adr/](adr) | Architecture Decision Records |
| [diagrams/](diagrams) | draw.io diagrams (`.drawio` + `.drawio.html` export) |
| [docs/](docs) | Wiki pages and notes, one per assignment |
| [governance/](governance) | Architecture principles (machine-readable) |
| [designs/](designs) | Design manifests that the ARB guardrail checks |
| [tools/](tools) | ARB guardrail |

## Assignment 1: Governance pack

- Wiki page: [assignment-01-governance-pack.md](docs/assignment-01-governance-pack.md) covers the principles, ADR summary, ARB checklist and guardrail
- Diagram: [Governance Pack](diagrams/Governance%20Pack.drawio)
- ADRs:
  - [ADR-001: Managed LLM API vs self-hosted](adr/ADR-001-managed-llm-api-vs-self-hosted.md)
  - [ADR-002: Vector DB choice](adr/ADR-002-vector-db-choice.md)
  - [ADR-003: Real-time vs batch](adr/ADR-003-realtime-vs-batch-processing.md)
- Automated guardrail: [`tools/arb_guardrail.py`](tools/arb_guardrail.py), which runs on every PR ([workflow](.github/workflows/arb-guardrail.yml))

## Running the guardrail

```bash
pip install pyyaml
python tools/arb_guardrail.py                                # lint ADRs + check designs/*.yaml
python tools/arb_guardrail.py --expect-fail tests/bad-design.yaml
```
