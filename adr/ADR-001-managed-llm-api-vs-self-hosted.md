# ADR-001: Managed LLM API behind a PII-redacting gateway (vs self-hosted)

- **Status:** Accepted
- **Date:** 2026-11-04
- **Scope:** LLM copy agent (campaign subject lines, push/WhatsApp template drafts, product blurbs) and segment summaries
- **Principles:** P1, P2, P3, P4

## Context

- Marketers want on-brand Arabic + English copy variants for each campaign and segment.
- **Volume:** about 300 campaigns/month × 40 segments × 5 variants ≈ 60k generations/month, with ~1.5k tokens in and 300 out per generation. Even a 6× seasonal peak is small.
- **Constraints:**
  - PDPL: customer PII must not reach a third party unless there is a lawful basis and a transfer assessment.
  - Arabic quality matters.
  - The team has no GPU or MLOps capacity today.

## Options

| | **A. Managed API (in-region cloud endpoint) + LLM gateway** | **B. Self-hosted open-weights model (e.g. 70B on GPUs)** | **C. Hybrid: small self-hosted model for PII tasks, API for the rest** |
|---|---|---|---|
| Quality (Arabic/English) | Highest, and we get upgrades for free | Good; we have to fine-tune and evaluate it ourselves | Mixed, with two models to evaluate |
| Cost at our volume | ≈ low hundreds of USD/month, pay per token | 2+ GPUs 24/7 for HA ≈ thousands of USD/month, plus people | Both bills |
| Privacy (P1) | Gateway strips/pseudonymises PII. Prompts carry segment attributes, never identities. Region-pinned endpoint, no training on our data | Strongest: data never leaves our VPC | Strong |
| Time to ship | Days | Months | Months |
| Lock-in | The gateway abstracts the provider, so we can swap | None | Low |

## Decision

**Option A.** Generation is per **segment, not per user** (P3), so prompts need no personal data. At this volume the per-token bill is about an order of magnitude below a GPU fleet. The LLM gateway enforces PII redaction, logging, token budgets and the provider allow-list. Every output goes into a **human approval queue** (P2) before it can become a campaign or a WhatsApp template. Each prompt version must pass the golden-set eval before release (P4).

## Consequences

- **Positive:**
  - No GPU operations.
  - Best Arabic quality.
  - The gateway is the single place to enforce privacy, cost and audit.
- **Negative:**
  - Depends on the vendor's SLA and price changes.
  - We can't do per-user 1:1 generation until we revisit this.
- **Revisit when:**
  - volume passes ~5M generations/month,
  - a use case needs raw PII in the prompt, or
  - an in-region endpoint isn't available.

  In any of these cases, re-evaluate option C.
