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

## Assignment 2: Use-case flow view (abandoned-cart nudge on WhatsApp)

- Diagram: [Abandoned Cart WhatsApp Flow](diagrams/Abandoned%20Cart%20WhatsApp%20Flow.drawio), with page 1 for the chosen option and page 2 for the rejected one
- Notes: [assignment-02-abandoned-cart-whatsapp-flow.md](docs/assignment-02-abandoned-cart-whatsapp-flow.md) (half a page): the two paths, the option comparison and the over-engineering check
- Decision: [ADR-004: Flink event timer + precomputed FBT](adr/ADR-004-abandoned-cart-trigger-flink-timer.md)
- Design manifest: [designs/abandoned-cart-whatsapp.yaml](designs/abandoned-cart-whatsapp.yaml), which passes the guardrail. Checking this design led to a refinement of rule R1: WhatsApp needs phone numbers, so external messaging processors need a lawful basis + DPA rather than redaction
