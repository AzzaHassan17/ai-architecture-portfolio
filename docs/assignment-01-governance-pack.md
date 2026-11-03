# Assignment 1: Governance pack for the Marketing Automation with AI & Agents system

**Diagram:** [Governance Pack.drawio](../diagrams/Governance%20Pack.drawio) shows how goals map to principles and ADRs, and how a design gets through the ARB · **Full ADRs:** [001](../adr/ADR-001-managed-llm-api-vs-self-hosted.md) · [002](../adr/ADR-002-vector-db-choice.md) · [003](../adr/ADR-003-realtime-vs-batch-processing.md)

**System in scope.** A Noon/Amazon-style marketplace runs personalised campaigns (recommendations, segments, AI-written copy, app/email/WhatsApp nudges) on the high-level architecture: Channels and API Gateway, E-commerce service and operational DB, CDC → Kafka → Flink, Airflow and CDP, feature store and vector DB, recommendation engine and WhatsApp.

## 1. Architecture principles

| # | Principle | Business goal |
|---|---|---|
| **P1** | **Privacy by design (PDPL):** minimum data, consent-gated, kept in-region; no raw PII to third-party models. | **G2:** customer trust, zero PDPL breaches |
| **P2** | **Agents propose, humans approve:** generated content reaches customers only after approval or as a pre-approved template. | **G5:** brand safety |
| **P3** | **Precompute by default:** batch unless real-time changes the outcome; real-time paths need a reason and a latency budget. | **G3:** lower cost per conversion |
| **P4** | **No eval, no launch:** every model or agent has an offline eval, an online KPI and a kill switch. | **G1:** proven conversion uplift |
| **P5** | **Protect the transactional core:** no AI/analytics reads on the operational DB (CDC only); AI failures fall back safely. | **G4:** checkout always available |

## 2. Architecture decisions

| ADR | Options | Decision | Trade-off accepted |
|---|---|---|---|
| **001** LLM hosting | Managed API · self-hosted · hybrid | **Managed in-region API behind a PII-redacting gateway**; copy generated per segment | Vendor dependency, in exchange for no GPU fleet and better Arabic quality |
| **002** Vector DB | pgvector · Qdrant · Pinecone | **pgvector on a dedicated Postgres** (not the operational DB) | Lower ceiling (~10M vectors), in exchange for one less system to run |
| **003** Real-time vs batch | All batch · all streaming · hybrid | **Hybrid:** Airflow by default, Flink only where minutes matter | Two pipelines, but streaming is paid for only where it pays back |

## 3. ARB checklist

Each design brings an ADR and a design manifest. ⚙ = checked automatically by the guardrail; ☐ = reviewer judgement. Outcome: **Approve**, **Approve with conditions** (owner + date) or **Reject**.

| Area | Checklist |
|---|---|
| **Security** | ☐ AuthN/Z on every API (JWT at gateway, mTLS) · ☐ secrets in a vault, never in prompts · ☐ prompt-injection defences · ☐ least-privilege agent tools, audit log |
| **Privacy (PDPL)** | ⚙ PII redacted before external LLMs; other processors need lawful basis + DPA (R1) · ⚙ approved regions only (R2) · ⚙ consent/opt-out checked before sends (R3) · ☐ retention and erasure reach CDP, feature store, vector DB · ☐ DPIA for profiling |
| **Evals** | ⚙ offline eval, online KPI, kill switch declared (R6) · ☐ Arabic + English golden set · ☐ A/B test with a complaint-rate guardrail metric |
| **Cost** | ⚙ real-time components justified with a latency budget (R5) · ☐ cost at average and 6× peak · ☐ LLM token budgets, budget alerts |
| **Human oversight** | ⚙ generated content approved or template-based (R4) · ☐ named owner per agent · ☐ frequency caps, manual pause |
| **Resilience** | ⚙ no operational-DB reads (R7) · ⚙ fallback for AI on user paths (R8) · ☐ timeouts on every hop |

## 4. Automated guardrail (optional, implemented)

[`tools/arb_guardrail.py`](../tools/arb_guardrail.py) runs on every pull request via [GitHub Actions](../.github/workflows/arb-guardrail.yml). It checks that each ADR has the required sections and cites valid principles, and applies rules R1–R8 to every design manifest in `designs/`. For example, a flow from the operational DB to anything but CDC fails R7 (P5). A deliberately broken design ([`tests/bad-design.yaml`](../tests/bad-design.yaml)) must fail all eight rules, which proves they fire. A failure blocks the merge and names the broken principle, so the ARB can focus on judgement calls.
