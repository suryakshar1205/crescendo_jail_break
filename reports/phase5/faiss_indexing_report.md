# Large-Scale FAISS Vector Indexing & Semantic Similarity ($S_t$) Architecture

> **Component Reference**: `src/crs/jailbreak_similarity.py`  
> **Backend Engines**: FAISS `IndexFlatIP` (canonical) & NumPy In-Memory Matrix (fallback)  
> **Status**: ☑ **[COMPLETED & VALIDATED]**  
> **Date**: September 2026

---

## 1. Executive Summary

As part of Step 3 (Master Checklist Section A3), the semantic similarity layer ($S_t$) has been upgraded to a high-performance vector retrieval architecture using **FAISS (Facebook AI Similarity Search) 1.11.0**. 

The system indexes multi-corpus attack datasets spanning:
1. Reconstructed Crescendo attack trajectories (`crescendo_attacks.json`)
2. Converted HarmBench/AdvBench trajectories (`converted_crescendo_attacks.json`)
3. Converted JailbreakBench multi-turn conversations (`converted_jailbreakbench.json`)
4. Synthetic adversarial mutations (`mutated_crescendo_variants.json`)
5. Multi-turn benchmark seeds (`mt_jailbench_seeds.json`)

Total attack vectors indexed: **292 unit-normalized dense vectors** in 384 dimensions (`sentence-transformers/all-MiniLM-L6-v2`).

---

## 2. Mathematical Formulation & Normalization

For incoming dialogue context $P_t$ and indexed attack turn vectors $V_i \in \mathbb{R}^{384}$, unit normalization guarantees that inner products compute exact cosine similarity:

$$\hat{e}(P_t) = \frac{e(P_t)}{\|e(P_t)\|_2}, \quad \hat{V}_i = \frac{V_i}{\|V_i\|_2}$$

$$\text{CosineSim}(P_t, V_i) = \hat{e}(P_t)^\top \hat{V}_i = \text{IndexFlatIP}.\text{search}(\hat{e}(P_t), k)$$

The raw jailbreak similarity score combines the top-$k$ nearest neighbors:

$$S_t^{\text{raw}} = 0.70 \cdot \max_{i \in \text{top-}k}(\text{Sim}_i) + 0.30 \cdot \frac{1}{k} \sum_{i=1}^k \text{Sim}_i + \mathbb{I}_{\text{payload}} \cdot 0.10$$

$$S_t = \text{clip}(S_t^{\text{raw}}, 0.0, 1.0)$$

where $\mathbb{I}_{\text{payload}}$ activates if any top match corresponds to an actionable final payload turn with similarity $> 0.60$.

---

## 3. Scalability & Latency Benchmark ($N=100$ to $N=10,000$)

Evaluated under strict SLA constraint: **$\le 25\text{ms}$ per defense turn**.

| Vector Index Size ($N$) | FAISS `IndexFlatIP` (ms) | NumPy Dot Product (ms) | Speedup Factor | SLA Target ($\le 25\text{ms}$) | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **100** | 0.0066 ms | 0.0880 ms | **13.36×** | 25.0 ms | ☑ **PASSED** |
| **500** | 0.0174 ms | 0.1056 ms | **6.08×** | 25.0 ms | ☑ **PASSED** |
| **1,000** | 0.0379 ms | 0.1082 ms | **2.85×** | 25.0 ms | ☑ **PASSED** |
| **5,000** | 0.1451 ms | 0.1606 ms | **1.11×** | 25.0 ms | ☑ **PASSED** |
| **10,000** | 0.5193 ms | 0.3109 ms | ~0.60× | 25.0 ms | ☑ **PASSED** |

### Numerical Precision & Equivalence
- **Max Discrepancy between FAISS and NumPy**: **`0.000000`** (Identical numerical precision).
- **Search Latency on Current Active Corpus (292 vectors)**: **0.012 ms** (over 2,000× faster than the 25ms SLA budget).

---

## 4. Index Persistence & Cold-Start Deserialization

To prevent re-encoding embeddings on every server restart:
- **Serialization**: `faiss.write_index(faiss_index, "data/cache/faiss_attacks_index.bin")` saves binary index in **17.65 ms**.
- **Deserialization**: `faiss.read_index("data/cache/faiss_attacks_index.bin")` loads all 292 vectors into memory in **21.19 ms**.
- **Metadata Cache**: Stored in `data/cache/faiss_attacks_metadata.json` with turn numbers, categories, payload flags, and original texts.

---

## 5. Verification & Test Suite

The FAISS vector engine was validated via `tests/test_faiss_vector_store.py`:
1. `test_multi_dataset_indexing`: PASSED (aggregates >50 attack vectors across all JSON files).
2. `test_query_similarity_boundaries`: PASSED ($S \in [0, 1]$ guaranteed).
3. `test_score_method_structure`: PASSED (exact match yields similarity $\ge 0.99$).
4. `test_faiss_vs_numpy_equivalence`: PASSED (FAISS `IndexFlatIP` matches NumPy dot product to 4 decimal places).
5. `test_index_save_and_load_persistence`: PASSED (save/load verified with 100% vector retention).
6. `test_query_latency_under_sla`: PASSED (query completes within SLA).
7. `test_pipeline_integration_with_similarity_layer`: PASSED (`CrescendoPRDPipeline` successfully reports `jailbreak_similarity_s_ms`).
