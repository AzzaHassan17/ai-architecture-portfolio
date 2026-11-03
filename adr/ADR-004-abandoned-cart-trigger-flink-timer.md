# ADR-004: Flink event timer + precomputed FBT for the abandoned-cart WhatsApp nudge

- **Status:** Accepted
- **Date:** 2026-11-04
- **Use case:** Abandoned-cart nudge on WhatsApp (Marketing Automation System)
- **Diagram:** [Abandoned Cart WhatsApp Flow](../diagrams/Abandoned%20Cart%20WhatsApp%20Flow.drawio)
- **Principles:** P3, P5, P1, P2

## Context

- **What we send:** one WhatsApp template per abandoned cart, 60 min after the last cart change, to opted-in users only, at most 1 per user per 24 h.
- **Volume:** ≈ 25k sends/day, up to ~2/s at the White Friday peak, at ≈ $0.04 per marketing message.
- **Constraints:**
  - Sending to someone who already bought wastes money and lowers the WhatsApp quality rating.
  - No analytical queries may hit the checkout database (P5).
  - Message text must be a Meta-approved template (P2).
  - Phone numbers go to WhatsApp only under consent and a data processing agreement (DPA) (P1).

## Options

| | **A. Flink keyed timer, stream-triggered** | **B. Airflow micro-batch every 15 min over the lake** | **C. Cron polling the operational DB** |
|---|---|---|---|
| Send timing | T+60 min, ±s | T+60–90 min | T+60–65 min |
| Wrong sends | ≈0 (cancel on order event, plus a PK re-check before send) | Carts bought in the last 5–30 min still get nudged | Low |
| Operational DB load | CDC + ≤ 2 PK reads/s via the owning service | CDC only | Full scan of idle carts every 5 min on the checkout DB |
| Cost | Marginal: Flink already runs session features, state ≈ 120 MB | Lowest compute, highest wasted messages | Cheap, but puts checkout at risk |
| Recommendations in the message | FBT top-3 per SKU, precomputed nightly in the CDP | Same | Same |

For the recommendation content, we also considered querying the vector DB for similar items at send time. We rejected it: FBT is co-purchase data and changes daily, so a key lookup is enough (P3).

## Decision

**Option A** with precomputed FBT from the CDP. Real-time is justified here (P3) because the cart's state at send time decides whether the message is right or wrong. Ingestion is CDC-only (P5). The Recommendation engine re-checks the cart through the E-commerce service API, never by querying the DB itself.

## Consequences

- **Positive:**
  - The nudge lands on time and correctly.
  - The request path uses key lookups only.
  - Graceful fallback: if the CDP is down, we send the cart-only template; if WhatsApp is down, we retry for 2 h, then drop.
- **Negative:**
  - The Flink job and its state have to be operated.
  - New components are needed: a webhook receiver for STOP/read events and a template registry.
- **Revisit when:** the nudge delay moves to 24 h or later (nightly batch is then enough), or if Flink is ever removed from the platform.
