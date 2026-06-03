# Architecture Diagram Placeholders

This directory contains architecture diagrams for the Crescendo Jailbreak Defense project.

## Planned Diagrams

| Filename | Description |
|---|---|
| `full_pipeline.png` | End-to-end pipeline: Phase 1 → Phase 5 |
| `phase_evolution.png` | Phase-over-phase metric evolution chart |
| `semantic_drift_pipeline.png` | Phase 2 embedding drift detection flow |
| `hybrid_risk_fusion.png` | Phase 3 behavioral + semantic fusion architecture |
| `contextual_memory_pipeline.png` | Phase 4 conversation memory + contextual risk flow |
| `ablation_summary.png` | Phase 5 component ablation impact chart |

## Generation

Diagrams can be generated from the Mermaid definitions below or from experimental results in `results/`.

### Full Pipeline (Mermaid)

```mermaid
graph LR
    A["Phase 1<br/>Baseline"] --> B["Phase 2<br/>Semantic Drift"]
    B --> C["Phase 3<br/>Hybrid Fusion"]
    C --> D["Phase 4<br/>Contextual Memory"]
    D --> E["Phase 5<br/>Robustness Testing"]
    
    style A fill:#e74c3c,color:#fff
    style B fill:#f39c12,color:#fff
    style C fill:#27ae60,color:#fff
    style D fill:#2980b9,color:#fff
    style E fill:#8e44ad,color:#fff
```

### Phase Evolution (Mermaid)

```mermaid
graph TD
    subgraph Metrics["Detection Rate Evolution"]
        P1["Phase 1: 22.0%"]
        P2["Phase 2: 31.4%"]
        P3["Phase 3: 54.0%"]
        P4["Phase 4: 73.4%"]
    end
    P1 --> P2 --> P3 --> P4

    style P1 fill:#e74c3c,color:#fff
    style P2 fill:#f39c12,color:#fff
    style P3 fill:#27ae60,color:#fff
    style P4 fill:#2980b9,color:#fff
```

### Semantic Drift Detection (Mermaid)

```mermaid
graph LR
    Input["Multi-turn<br/>Prompts"] --> Embed["Sentence<br/>Embeddings"]
    Embed --> Anchor["Anchor<br/>Drift"]
    Embed --> Local["Local<br/>Drift"]
    Embed --> Vel["Velocity"]
    Anchor --> Weighted["Weighted<br/>Risk Score"]
    Local --> Weighted
    Vel --> Weighted
    Weighted --> Decision{"Threshold<br/>Check"}
    Decision -->|Safe| Pass["Allow"]
    Decision -->|Flagged| Block["Block/Escalate"]
```

### Hybrid Risk Fusion (Mermaid)

```mermaid
graph TD
    P2["Phase 2<br/>Semantic Score"] --> Fusion["Risk Fusion<br/>0.70 × semantic + 0.30 × behavioral"]
    P3B["Behavioral<br/>Rule Score"] --> Fusion
    Fusion --> Level{"Risk Level<br/>Classification"}
    Level -->|safe| Safe["Safe"]
    Level -->|medium| Medium["Medium Risk"]
    Level -->|high| High["High Risk"]
```

### Contextual Memory Pipeline (Mermaid)

```mermaid
graph TD
    Turn["New Turn"] --> Memory["Conversation<br/>Memory Engine"]
    Memory --> Historical["Historical<br/>Risk (decay=0.80)"]
    Memory --> Trend["Trend<br/>Score"]
    Memory --> Persist["Persistence<br/>Memory"]
    Memory --> Bypass["Bypass<br/>Detection"]
    
    P3["Phase 3<br/>Fusion Score"] --> Context["Contextual Risk<br/>Computation"]
    Historical --> Context
    Trend --> Context
    Persist --> Context
    Bypass --> Context
    Context --> Final["Final<br/>Classification"]
```
