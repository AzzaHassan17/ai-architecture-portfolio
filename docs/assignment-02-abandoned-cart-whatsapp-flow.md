# Assignment 2: Abandoned-cart nudge on WhatsApp (flow view)

**Diagram:** [Abandoned Cart WhatsApp Flow.drawio](../diagrams/Abandoned%20Cart%20WhatsApp%20Flow.drawio) (page 1 chosen, page 2 rejected) · **ADR:** [ADR-004](../adr/ADR-004-abandoned-cart-trigger-flink-timer.md)

**Scenario.** An opted-in shopper leaves a cart. 60 min later they get one approved WhatsApp template with their items, up to 3 "frequently bought together" (FBT) items and a link that restores the cart. Nobody who already bought gets nudged; max 1 per 24 h.

**Background path.** Nightly, Airflow precomputes FBT per SKU and syncs consent and caps into the CDP. Cart writes reach Flink through CDC → Kafka. Flink runs a 60-min timer per cart, and an order event cancels it.

**Real-time paths.** *Trigger* (async, P95 ≤ 5 s): Flink → Kafka → Recommendation engine, which checks the CDP, re-checks the cart via the E-commerce service and sends through WhatsApp. *Click-back* (user waiting, P95 ≤ 300 ms, ~70 ms used): Channel → API Gateway → E-commerce service loads the cart by key.

| | **A. Flink timer + FBT from CDP** | B. Airflow every 15 min | C. Vector DB per send |
|---|---|---|---|
| Latency | On time (T+60 min) | T+60–90 min | Same as A |
| Cost | Flink already runs | Nudges buyers: ~$10/day per 1% wrong sends | Vector DB sized for peaks |
| Operational DB load | CDC + ≤ 2 key reads/s | CDC only | CDC + ≤ 2 key reads/s |

**Decision: A.** It's the only option that is on time and doesn't nudge people who already bought. FBT changes daily, so precomputing it beats a live vector lookup.

**Over-engineering check.** *Missing:* a WhatsApp webhook receiver (opt-outs for PDPL), a registry of Meta-approved templates, signed deep links. *Not needed:* vector DB, feature store, LLM (templates are pre-approved).
