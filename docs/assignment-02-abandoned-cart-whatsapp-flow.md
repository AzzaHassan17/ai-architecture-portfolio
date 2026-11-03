# Assignment 2: Use-case flow view for the abandoned-cart nudge on WhatsApp

**Diagram:** [Abandoned Cart WhatsApp Flow.drawio](../diagrams/Abandoned%20Cart%20WhatsApp%20Flow.drawio), Page 1 is the design we chose, page 2 the one we rejected. The `.drawio.html` copy opens without draw.io.
**Decision record:** [ADR-004](../adr/ADR-004-abandoned-cart-trigger-flink-timer.md) · **Design manifest:** [designs/abandoned-cart-whatsapp.yaml](../designs/abandoned-cart-whatsapp.yaml), which passes the [ARB guardrail](../tools/arb_guardrail.py)

**Scenario.** A shopper leaves items in their cart. If they have opted in to WhatsApp marketing, 60 min later they get one approved WhatsApp template: their cart items plus up to 3 "frequently bought together" (FBT) items, and a deep link that restores the cart. **Targets:**
- Trigger path: P95 ≤ 5 s from the timer firing to WhatsApp accepting the message.
- Click-back path: P95 ≤ 300 ms server side.
- Never nudge someone who has already bought; at most 1 nudge per user per 24 h.

## How the flow works: background vs. real-time

- **Background path:**
  - *Batch, nightly:* Airflow computes FBT top-3 per SKU and syncs consent, caps and language into the CDP.
  - *Streaming, seconds:* the cart write reaches the operational DB, then **CDC** (reads the log) → **Kafka** → **Flink**. Flink keeps a 60-min timer per cart; an order event cancels it.
- **Trigger path (async):** Flink emits `cart.abandoned` to Kafka and the Recommendation engine consumes it. The engine checks opt-in, cap, quiet hours and FBT in the **CDP**, re-checks the cart through the **E-commerce service** (one primary-key read), and sends an approved AR/EN template through **WhatsApp**.
- **Real-time request path (user waiting):** the user taps the deep link: Channel → API Gateway → E-commerce service, which verifies the signed token and loads the cart by primary key. The FBT SKUs travel in the token, so this path makes no recommendation call.

## Choosing the trigger: three options

| | **A. Flink timer + precomputed FBT from CDP (chosen)** | **B. Airflow every 15 min over the lake** | **C. Real-time vector-DB "similar items" per send** |
|---|---|---|---|
| When the nudge lands | At T+60 min, ±seconds | T+60–90 min (lake lag + schedule) | Same as A |
| Wrong sends (already bought) | ≈0: cart is re-checked just before sending | Carts bought in the last 5–30 min still get nudged | Same as A |
| Cost | Flink is already running; state ≈ 120 MB | Cheapest compute, but wasted messages (each 1% ≈ $10/day at ~25k sends/day) | Vector DB sized for send peaks, for little gain |
| Operational DB load | CDC + ≤ 2 PK reads/s | CDC only | CDC + ≤ 2 PK reads/s |

**We chose A.** It's the only option that is both on time and correct. Each wrong send costs money, annoys the customer and hurts our WhatsApp quality rating. FBT is co-purchase data and only changes daily, so precomputing it beats querying the vector DB at send time (C). **Rejected:** polling the operational DB for idle carts, because it puts analytical load on checkout (P5).

## Gaps and extras compared with the high-level architecture

- **Our flow needs, but the high-level view lacks:**
  - **WhatsApp webhook receiver** to put delivered/read/STOP events onto Kafka. Opt-out must reach the CDP within minutes to meet PDPL.
  - **Template registry** for Meta-approved templates (P2).
  - **Signed deep-link/token service**, which can live in the E-commerce service.
  - **Dashboards and alerts** for recovery rate, opt-out rate and wrong sends.
- **In the high-level view, but this flow doesn't use:**
  - **Vector DB** and **feature store**: v1 has no ranking model.
  - **LLM**: templates must be pre-approved by Meta, so nothing is generated at send time.
  - **Airflow** on the trigger path: it only does the nightly precompute.

## Per-hop latency budget (P95)

| Trigger path | Flink → Kafka | consume | CDP lookups | cart re-check | template | WhatsApp API | **Total** |
|---|---|---|---|---|---|---|---|
| ms | 20 | 50 | 15 | 40 | 10 | 600 | **735** of a 5,000 ms budget (headroom for retries) |

| Click-back path | Gateway + TLS | verify token | load cart (PK) | build response | **Total** |
|---|---|---|---|---|---|
| ms | 10 | 5 | 15 | 40 | **70** of 300 ms |

**Sizing (our scenario):**
- About 600k DAU. 15% build a cart, 70% of those carts are abandoned, and ~40% of those users are opted in and under the cap: ≈ 25k sends/day, ~0.3/s on average and ~2/s at the White Friday peak (6×).
- Marketing template cost ≈ $0.04 per message (it varies by country).
