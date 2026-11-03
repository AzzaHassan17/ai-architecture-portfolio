# ADR-002: pgvector on a dedicated Postgres as the vector DB

- **Status:** Accepted
- **Date:** 2026-11-04
- **Scope:** Product and content embeddings for similar-item retrieval, the cold-start "more like this" feature, and semantic search over campaign assets
- **Principles:** P3, P5, P1

## Context

- **Data:** about 2M catalogue items plus ~200k content assets, at 768 dims. With metadata filters (category, in-stock, country), that comes to ≈ 7 GB of vectors plus an HNSW index.
- **Load:** most retrieval runs in Airflow batch jobs (P3). Online queries come only from cold-start and search, about 50 QPS at peak, with a P95 ≤ 50 ms target.
- **Constraints:** the data must stay in-region (P1), and the operational DB must not take this load (P5).

## Options

| | **A. pgvector on a dedicated managed Postgres** | **B. Qdrant (self-hosted, Kubernetes)** | **C. Managed SaaS vector DB (e.g. Pinecone)** |
|---|---|---|---|
| Fit at 2–10M vectors | Good; HNSW P95 ≈ 10–30 ms with filters | Excellent; built for ANN and filtering | Excellent |
| Ops burden | Lowest: same engine and skills we already have | We run a new stateful cluster | None |
| Cost | One mid-size instance plus a replica | 3-node cluster plus people | Usage-based; highest at steady load |
| Residency (P1) | In our region and VPC | In our region and VPC | Region options are limited, so a transfer assessment is needed |
| Hybrid filters / joins | SQL joins with product metadata | Payload filters | Metadata filters |
| Scale ceiling | ≈ 10M vectors before tuning gets painful | 100M+ | 100M+ |

## Decision

**Option A.** At our size, pgvector meets the 50 ms P95 target at roughly a third of the cost of a dedicated cluster, and it adds no new technology to operate. It's a **separate instance** from the operational DB and is fed by Airflow from CDC data, so there's zero added load on checkout (P5). The application talks to it only through a thin `VectorStore` interface, which keeps a later move to Qdrant cheap.

## Consequences

- **Positive:**
  - One less system to run.
  - SQL filters and joins on metadata.
  - In-region by default.
- **Negative:**
  - Lower scale ceiling.
  - Index rebuilds compete with queries, so we schedule them off-peak.
- **Revisit when:**
  - vectors pass ~10M,
  - online P95 goes above 50 ms at peak, or
  - we need multi-vector or hybrid sparse+dense search.

  If any of these happen, migrate to Qdrant (option B) behind the same interface.
