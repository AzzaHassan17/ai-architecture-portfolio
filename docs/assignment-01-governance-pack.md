# Assignment 1: Governance pack for the Marketing Automation with AI & Agents system

**Diagram:** [Governance Pack.drawio](../diagrams/Governance%20Pack.drawio). Editable in draw.io; the `.drawio.html` copy opens without it. It shows how goals map to principles and ADRs, and how a design gets through the ARB.
**ADRs:** [001 LLM hosting](../adr/ADR-001-managed-llm-api-vs-self-hosted.md) · [002 Vector DB](../adr/ADR-002-vector-db-choice.md) · [003 Real-time vs batch](../adr/ADR-003-realtime-vs-batch-processing.md)
**Guardrail:** [`tools/arb_guardrail.py`](../tools/arb_guardrail.py), run on every PR by [GitHub Actions](../.github/workflows/arb-guardrail.yml).

**System in scope.** A Noon/Amazon-style marketplace runs personalised campaigns: recommendations, segments, AI-written campaign copy, and nudges over app, email and WhatsApp. Components: Channels and API Gateway, E-commerce service and operational DB, CDC → Kafka → Flink, Airflow and CDP, feature store and vector DB, recommendation engine, an LLM copy agent, and WhatsApp.

## 1. Architecture principles

| # | Principle | Business goal it serves | How we check it |
|---|---|---|---|
| **P1** | **Privacy by design (PDPL).** Collect the minimum, gate every use on consent, keep data in-region. Raw PII never goes to a third-party model. | **G2:** customer trust, zero reportable PDPL breaches | Guardrail R1–R3; ARB privacy section |
| **P2** | **Agents propose, humans approve.** Generated content reaches customers only after human approval, or as a pre-approved template. | **G5:** brand safety | Guardrail R4; ARB oversight section |
| **P3** | **Precompute by default.** Use batch unless real-time changes the outcome. Every real-time path states why and has a latency budget. | **G3:** lower cost per conversion | Guardrail R5; ARB cost section |
| **P4** | **No eval, no launch.** Each model or agent has an offline eval, an online KPI and a kill switch. | **G1:** proven conversion uplift | Guardrail R6; ARB evals section |
| **P5** | **Protect the transactional core.** No AI or analytics reads from the operational DB; data leaves it only through CDC. AI failure falls back to a safe default. | **G4:** checkout always available | Guardrail R7–R8 |

## 2. Architecture decisions (summary)

| ADR | Options considered | Decision | Main trade-off accepted | Principles |
|---|---|---|---|---|
| [001](../adr/ADR-001-managed-llm-api-vs-self-hosted.md) LLM hosting | Managed API · self-hosted open-weights · hybrid | **Managed API in an in-region cloud, behind an LLM gateway that redacts PII.** Copy is generated per segment, not per user. | Vendor dependency and per-token cost, in exchange for no GPU fleet and better quality | P1, P2, P3, P4 |
| [002](../adr/ADR-002-vector-db-choice.md) Vector DB | pgvector · Qdrant (self-hosted) · managed SaaS (Pinecone) | **pgvector on a dedicated Postgres**, separate from the operational DB | Lower ANN ceiling (≈10M vectors) in exchange for one less system to run | P3, P5, P1 |
| [003](../adr/ADR-003-realtime-vs-batch-processing.md) Real-time vs batch | All batch · all streaming · hybrid | **Hybrid:** Airflow batch for segments, scores and top-K; Flink only for event-triggered journeys and session features | Two pipelines to run, in exchange for paying for streaming only where minutes matter | P3, P5 |

## 3. ARB checklist

Every design going to the Architecture Review Board needs a design manifest (`designs/*.yaml`) and an ADR. Items marked ⚙ are checked automatically by the guardrail before review. The others are for reviewers. Possible outcomes: **Approve**, **Approve with conditions** (each with an owner and a date), or **Reject**.

| Area | Checklist item |
|---|---|
| **Security** | ☐ AuthN/Z on every API (JWT at the gateway, service-to-service mTLS) · ☐ secrets in a vault, none in code or prompts · ☐ prompt-injection defences on every LLM input that comes from users or the web (input filtering, tool allow-list, output validation) · ☐ agents run with least-privilege tools, and writes need approval · ☐ audit log for every agent action |
| **Privacy (PDPL)** | ⚙ PII is always redacted before an external LLM call; other external processors (e.g. WhatsApp) need a lawful basis and a DPA (R1) · ⚙ every data store and model endpoint is in an approved region, otherwise a cross-border transfer assessment is attached (R2) · ⚙ customer-facing sends check consent and opt-out (R3) · ☐ purpose and lawful basis recorded for each data category · ☐ retention period set and deletion flows through to the feature store, CDP and vector DB · ☐ data-subject requests (access/erase) covered · ☐ DPIA done for profiling |
| **Evals** | ⚙ offline eval set, online KPI and kill switch declared for every model or agent (R6) · ☐ golden set covers Arabic + English, plus edge cases (prices, claims, sensitive categories) · ☐ LLM-judge plus human spot-check on each prompt change · ☐ A/B plan with a guardrail metric (unsubscribe/complaint rate) · ☐ drift and quality monitoring in production |
| **Cost** | ⚙ every real-time component states why and has a latency budget (R5) · ☐ cost per 1k requests or messages estimated at average and peak (peak = 6× average, White Friday) · ☐ token budget and caching for LLM calls · ☐ budget alerts and per-campaign cost attribution |
| **Human oversight** | ⚙ generated customer-facing content is human-approved or template-based (R4) · ☐ named owner per agent · ☐ frequency caps and send windows enforced · ☐ escalation path for complaints · ☐ manual override or pause for any automated campaign |
| **Resilience** | ⚙ no direct operational-DB reads from AI or analytics (R7) · ⚙ fallback declared for each AI call on a user path (R8) · ☐ timeouts and circuit breakers on every hop |

## 4. Automated guardrail (optional part, implemented)

[`tools/arb_guardrail.py`](../tools/arb_guardrail.py) runs in CI on every pull request and does two things:

1. **ADR lint.** Each ADR must have Status, Context, Options, Decision and Consequences sections, plus a `Principles:` line that cites only IDs from [`principles.yaml`](../governance/principles.yaml).
2. **Design check.** It reads each design manifest (components and data flows) and applies rules R1–R8. Example: a flow from `operational_db` to anything other than CDC or the owning service fails R7 (P5). A customer-facing LLM output without `human_review` or `approved_templates` fails R4 (P2).

A deliberately bad manifest ([`tests/bad-design.yaml`](../tests/bad-design.yaml)) runs in CI too, and the job checks that it fails all eight rules, which proves the rules actually fire. A failing check blocks the merge and points the author to the principle that was broken, so the ARB can spend its time on judgement calls.
