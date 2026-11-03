# ADR-003: Hybrid processing (batch by default, streaming for event-triggered journeys)

- **Status:** Accepted
- **Date:** 2026-11-04
- **Scope:** How customer events become segments, scores, recommendations and triggered messages
- **Principles:** P3, P5

## Context

- **Inputs:** orders, carts and profile changes arrive through CDC → Kafka. Clickstream arrives from the channels.
- **Jobs that tolerate hours of delay:** segments, churn and propensity scores, and per-user top-K candidates.
- **Jobs where minutes matter:**
  - abandoned-cart nudges (conversion falls sharply after the first hour),
  - back-in-stock alerts,
  - in-session features (last viewed category).
- **Traffic:** about 600k DAU, ~1.8k events/s on average, ~11k/s at the White Friday peak (6×).

## Options

| | **A. All batch (Airflow, hourly/nightly)** | **B. All streaming (Flink for everything)** | **C. Hybrid: Airflow by default, Flink only for latency-critical paths** |
|---|---|---|---|
| Freshness | 1–24 h. Too slow for cart and session use cases | Seconds everywhere, including where nobody benefits | Seconds where it pays, hours elsewhere |
| Cost | Lowest; off-peak compute | Highest; always-on state sized for peak | Medium; Flink sized only for a few keyed jobs |
| Complexity | One paradigm, easy backfills | Model training and backfills are hard to do in streaming | Two paradigms, sharing Kafka topics and the feature store |
| Operational DB load (P5) | Zero if it reads CDC; a risk if someone "just queries prod" | Zero | Zero: both read CDC → Kafka |

## Decision

**Option C.** Airflow owns training, batch scoring, segment builds and top-K precompute, which it writes to the CDP and the offline feature store (P3). Flink runs only jobs whose output loses value within minutes: abandonment timers, back-in-stock triggers and session features in the online store. A new Flink job must say in its ADR why a batch job wouldn't do (guardrail R5). Both paths read from CDC → Kafka, never from the operational DB (P5).

## Consequences

- **Positive:**
  - We pay for streaming only where it changes revenue.
  - Backfills and training stay simple in batch.
- **Negative:**
  - The same feature can be computed twice (once in Flink, once in Airflow), so a feature-store contract and parity tests are needed.
  - The team has to run two runtimes.
- **Revisit when:** more than ~5 use cases need sub-minute freshness. At that point, consider moving to streaming-first with a Kappa-style replay.
