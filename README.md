# Manufacturing Process Health and Operational Efficiency Analysis

### A Data-Driven Framework for 6G-Oriented Smart Factories

An integrated manufacturing analytics platform for monitoring machine health, production performance, energy consumption, network quality of service, and operational efficiency through an interactive data-driven dashboard.

<p align="center">
  <a href="https://smart-factory-manufacturing-analytics-tjambjpnvyme6cdqysgqvp.streamlit.app/">
    <img src="https://img.shields.io/badge/Live_Dashboard-Visit_App-brightgreen?style=for-the-badge&logo=streamlit" alt="Live Dashboard">
  </a>
  <a href="https://github.com/nitin25J/smart-factory-manufacturing-analytics">
    <img src="https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github" alt="GitHub Repository">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-Analytics-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-Dashboard-red?style=flat&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/Research-Working_Paper-orange?style=flat" alt="Research Working Paper">
</p>

---

## Project Overview

Manufacturing environments generate large volumes of operational data across machines, production processes, energy consumption, product quality, and industrial network systems. Analyzing these dimensions independently can make it difficult to develop a unified understanding of manufacturing operations.

**Manufacturing Process Health and Operational Efficiency Analysis** is a Python-based, Streamlit-powered analytics platform designed to bring these operational dimensions together through an integrated dashboard.

The system processes manufacturing telemetry and provides analytical capabilities across five key domains:

- **Machine Health:** Temperature, vibration, and multivariate condition screening.
- **Production Performance:** Production speed, operational modes, and throughput analysis.
- **Energy Efficiency:** Power consumption and Specific Energy Consumption (SEC).
- **Network Quality of Service:** Network latency, packet loss, and empirical distribution profiling.
- **Manufacturing Quality:** Defect rates, process error rates, and efficiency-status analysis.

The project establishes a data-driven analytical framework for **6G-oriented smart manufacturing**, with an emphasis on interpretable metrics, statistical analysis, and transparent evaluation of data limitations.

---


## Problem Statement

Traditional manufacturing analytics often operate across separate functional domains, creating fragmented visibility into overall production operations.

Key challenges include:

1. **Industrial Network QoS:** Network latency and packet loss are monitored separately from manufacturing performance.
2. **Machine Health Monitoring:** Temperature and vibration measurements are analyzed independently, limiting integrated equipment assessment.
3. **Production Monitoring:** Machine operating states and production throughput are tracked without sufficient cross-domain context.
4. **Energy Management:** Power consumption and energy efficiency are evaluated separately from production output.
5. **Quality Assurance:** Defect rates and process errors are assessed independently of machine, network, and energy conditions.

This fragmented approach makes it difficult to interpret relationships between operational dimensions within a unified analytical environment.

The project addresses this challenge by developing an integrated manufacturing analytics platform that brings these five domains into a common dashboard while preserving their individual metrics, units, and analytical meaning.

---

## Project Objectives

The primary objectives of this project are:

1. **Unified Manufacturing Analytics:** Integrate machine health, production, energy, network QoS, and quality metrics into a common analytical platform.
2. **Machine Condition Assessment:** Analyze temperature and vibration measurements using statistical and multivariate techniques.
3. **Production Performance Analysis:** Examine production speed, machine operating modes, and throughput patterns.
4. **Energy Efficiency Evaluation:** Calculate and analyze Specific Energy Consumption (SEC), including its mathematical expectation decomposition.
5. **Network QoS Profiling:** Evaluate network latency and packet loss using non-parametric empirical distribution analysis.
6. **Quality and Efficiency Monitoring:** Analyze defect rates, process error rates, and supplied efficiency categories.
7. **Interactive Visualization:** Provide an accessible dashboard with synchronized filters, analytical visualizations, and sanitized CSV exports.
8. **Scientific Data Validation:** Audit telemetry characteristics, identify data-quality limitations, and distinguish descriptive analysis from validated physical or predictive claims.

The broader objective is to establish an interpretable analytical foundation for future 6G-oriented smart manufacturing environments without claiming a physical 6G deployment.

---

## System Architecture

The Manufacturing Process Health and Operational Efficiency Analysis platform follows a modular, multi-layer architecture designed to integrate manufacturing telemetry processing, KPI computation, statistical analytics, and interactive dashboard visualization.

The architecture separates data ingestion, validation, application-level processing, analytical computation, and presentation into dedicated components. A centralized Streamlit application manages global filters, processes the selected telemetry records, calculates domain-specific KPIs, and dispatches the results to four specialized analytical modules.

### Architecture Diagram

```mermaid
flowchart TB

    A["Manufacturing Telemetry Dataset<br/>CSV Input"]

    subgraph L1["01 — DATA ACCESS LAYER"]
        B["data_loader.py<br/>Data Ingestion"]
        C["Data Validation and Integrity<br/>Schema Enforcement<br/>Missing Value Checks<br/>Date and Time Parsing<br/>Cached Data Loading"]
        B --> C
    end

    subgraph L2["02 — APPLICATION AND COMPUTATION LAYER"]
        D["app.py<br/>Central Streamlit Application"]
        E["Global Filters<br/>Machine ID<br/>Operation Mode<br/>Date Range"]
        F["Filtered Manufacturing Data"]
        G["kpi_engine.py<br/>Vectorized KPI Computation"]
        H["Five-Domain KPI Results<br/>Machine Health<br/>Production Throughput<br/>Product Quality<br/>Network Reliability<br/>Energy Efficiency"]

        D --> E
        E --> F
        F --> G
        G --> H
    end

    subgraph L3["03 — ANALYTICAL DASHBOARD MODULES"]
        M1["Module 1<br/>Factory Health and Network Overview"]
        M2["Module 2<br/>Machine Health and Condition Monitoring"]
        M3["Module 3<br/>Production Throughput and Energy Monitoring"]
        M4["Module 4<br/>Quality Assurance and Efficiency Diagnostics"]
    end

    subgraph L4["04 — SHARED ANALYTICS AND UI COMPONENTS"]
        I["analytics.py<br/>ECDF Profiling<br/>Latency Dispersion Analysis<br/>Mahalanobis Screening<br/>Machine and Production Summaries"]
        J["components.py<br/>KPI Cards and Section Headers<br/>Global Filters<br/>Error and Empty States<br/>Sanitized CSV Exports"]
    end

    subgraph L5["05 — PRESENTATION AND OUTPUT"]
        K["Interactive Streamlit Dashboard"]
        O["Analytical Visualizations<br/>KPI Metrics<br/>Statistical Tables<br/>CSV Downloads"]
        K --> O
    end

    A --> B
    C --> D

    F --> M1
    F --> M2
    F --> M3
    F --> M4

    H --> M1
    H --> M2
    H --> M3
    H --> M4

    D -->|"Module Navigation and Dispatch"| M1
    D -->|"Module Navigation and Dispatch"| M2
    D -->|"Module Navigation and Dispatch"| M3
    D -->|"Module Navigation and Dispatch"| M4

    M1 -.->|"Uses"| I
    M2 -.->|"Uses"| I
    M3 -.->|"Uses"| I
    M4 -.->|"Uses"| I

    M1 -.->|"Uses"| J
    M2 -.->|"Uses"| J
    M3 -.->|"Uses"| J
    M4 -.->|"Uses"| J

    J -.->|"Shared Presentation Utilities"| K
    M1 --> K
    M2 --> K
    M3 --> K
    M4 --> K

    classDef source fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e,stroke-width:2px
    classDef data fill:#eff6ff,stroke:#2563eb,color:#1e3a8a
    classDef core fill:#f3e8ff,stroke:#9333ea,color:#581c87
    classDef modules fill:#ecfdf5,stroke:#059669,color:#064e3b,stroke-width:1.5px
    classDef services fill:#fff7ed,stroke:#ea580c,color:#7c2d12
    classDef output fill:#fef9c3,stroke:#ca8a04,color:#713f12,stroke-width:2px

    class A source
    class B,C data
    class D,E,F,G,H core
    class M1,M2,M3,M4 modules
    class I,J services
    class K,O output
```

### Architecture Components

| Layer | Component | Responsibility |
|---|---|---|
| Data Access | `data_loader.py` | Dataset ingestion, schema validation, integrity checks, and caching. |
| Application | `app.py` | Application initialization, global filtering, KPI orchestration, and module navigation. |
| KPI Engine | `kpi_engine.py` | Vectorized computation across five manufacturing KPI domains. |
| Analytics | `analytics.py` | Reusable statistical and analytical functions, including ECDF and Mahalanobis distance calculations. |
| Dashboard Modules | `modules/` | Four specialized interfaces for manufacturing diagnostics. |
| Shared UI | `components.py` | Reusable UI elements, filtering utilities, error handling, and CSV exports. |

### Analytical Dashboard Modules

1. **Factory Health and Network Overview:** Evaluates network latency, packet loss, empirical distributions, and within-machine latency dispersion.
2. **Machine Health and Condition Monitoring:** Examines temperature, vibration, predictive maintenance scores, and Mahalanobis distance-based geometric screening.
3. **Production Throughput and Energy Monitoring:** Analyzes production speed, operational modes, power consumption, and Specific Energy Consumption (SEC).
4. **Quality Assurance and Efficiency Diagnostics:** Evaluates defect rates, process error rates, efficiency-status distributions, and contingency relationships.

### Architecture Design Principles

- **Modularity:** Separates data processing, computation, analytics, and visualization responsibilities.
- **Reusability:** Uses common analytical functions and shared UI components across dashboard modules.
- **Vectorized Processing:** Leverages Pandas and NumPy for efficient processing of large telemetry datasets.
- **Interactive Analysis:** Provides synchronized global filters and specialized analytical views.
- **Data Integrity:** Enforces schema validation, data-quality checks, and sanitized data exports.
- **Interpretability:** Preserves individual KPI definitions and physical units instead of combining unrelated metrics into opaque composite scores.
