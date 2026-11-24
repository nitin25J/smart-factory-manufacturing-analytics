# Manufacturing Process Health and Operational Efficiency Analysis

### A Data-Driven Framework for 6G-Oriented Smart Factories.

An integrated manufacturing analytics platform for monitoring machine health, production performance, energy consumption, network quality of service, and operational efficiency through an interactive data-driven dashboard.
 

<p align="center">
  <a href="https://smart-factory-manufacturing-analytics-tjambjpnvyme6cdqysgqvp.streamlit.app/">
    <img src="https://img.shields.io/badge/Live_Dashboard-Visit_App-brightgreen?style=for-the-badge&logo=streamlit" alt="Live Dashboard">
  </a>
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

The application follows a modular, layered architecture. Manufacturing telemetry data is ingested and validated before entering the Streamlit application. Users can filter the dataset, generate KPI results, and navigate between four analytical dashboard modules. The selected module uses shared analytical and UI utilities to render the results.


### Architecture Diagram


```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#0B0F14","primaryColor":"#0B3562","primaryTextColor":"#FFFFFF","primaryBorderColor":"#3B82F6","lineColor":"#3B82F6","secondaryColor":"#102D4D","tertiaryColor":"#0B3562","clusterBkg":"#101A29","clusterBorder":"#2563EB","edgeLabelBackground":"#0B0F14","fontFamily":"Arial"}}}%%

flowchart TB

    A["Manufacturing Telemetry Dataset<br/>CSV Input"]
    B["data_loader.py<br/>Data Ingestion and Cached Loading"]
    C["Data Validation and Integrity<br/>Schema Enforcement<br/>Missing-Value Checks<br/>Date-Time Parsing"]
    D[("Validated Manufacturing Dataset")]

    E["app.py<br/>Central Streamlit Application"]
    F["Global Filter Controls<br/>Machine ID · Operation Mode<br/>Date Range"]
    G["Filtered Manufacturing Data"]

    H["kpi_engine.py<br/>Vectorized KPI Computation"]
    I["Five KPI Domains<br/>Machine Health · Production Throughput<br/>Product Quality · Network Reliability<br/>Energy Efficiency"]

    J{"Dashboard Module Selection"}

    subgraph MODULES["ANALYTICAL DASHBOARD MODULES"]
        direction LR
        M1["Factory Health and<br/>Network Overview"]
        M2["Machine Health and<br/>Condition Monitoring"]
        M3["Production Throughput and<br/>Energy Monitoring"]
        M4["Quality Assurance and<br/>Efficiency Diagnostics"]
    end

    subgraph UTILITIES["SHARED ANALYTICAL AND UI UTILITIES"]
        direction LR
        N["analytics.py<br/>Statistical Analysis<br/>ECDF · Mahalanobis Screening<br/>Machine and Production Summaries"]
        O["components.py<br/>Reusable UI Components<br/>KPI Cards · Section Headers<br/>Error States · CSV Export"]
    end

    P["Interactive Streamlit Dashboard<br/>KPI Metrics · Visualizations<br/>Analytical Tables · CSV Downloads"]

    A --> B --> C --> D --> E
    E --> F --> G
    G --> H --> I

    G --> J
    I --> J

    J --> M1
    J --> M2
    J --> M3
    J --> M4

    M1 -.-> N
    M2 -.-> N
    M3 -.-> N
    M4 -.-> N

    M1 -.-> O
    M2 -.-> O
    M3 -.-> O
    M4 -.-> O

    N --> P
    O --> P

    classDef main fill:#0B3562,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef database fill:#0B3562,stroke:#60A5FA,color:#FFFFFF,stroke-width:2px;
    classDef decision fill:#123F70,stroke:#60A5FA,color:#FFFFFF,stroke-width:2px;
    classDef module fill:#102F52,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef utility fill:#123B60,stroke:#60A5FA,color:#FFFFFF,stroke-width:2px;
    classDef output fill:#164E8A,stroke:#60A5FA,color:#FFFFFF,stroke-width:2.5px;

    class A,B,C,E,F,G,H,I main;
    class D database;
    class J decision;
    class M1,M2,M3,M4 module;
    class N,O utility;
    class P output;

    style MODULES fill:#101A29,stroke:#2563EB,stroke-width:2px,color:#FFFFFF
    style UTILITIES fill:#101A29,stroke:#2563EB,stroke-width:2px,color:#FFFFFF

    linkStyle default stroke:#3B82F6,stroke-width:2px;
```


### Architecture Execution Sequence

1. **Data Ingestion:** `data_loader.py` loads the manufacturing telemetry CSV and performs schema validation, integrity checks, date-time parsing, and cached data loading.
2. **Application and Filtering:** `app.py` initializes the Streamlit application and provides global filters for machine ID, operation mode, and date range. The selected filters produce the filtered manufacturing dataset.
3. **KPI Computation:** `kpi_engine.py` processes the filtered dataset using vectorized computations to generate five KPI domains: machine health, production throughput, product quality, network reliability, and energy efficiency.
4. **Dashboard Dispatch:** The application passes the filtered dataset and KPI results to the dashboard module selected through navigation. Only the selected module is rendered during a given application view.
5. **Shared Utilities:** The active module uses `analytics.py` for reusable statistical computations and `components.py` for common interface elements, filtering utilities, and CSV exports.
6. **Presentation:** The Streamlit interface displays the resulting KPI metrics, visualizations, analytical summaries, tables, and downloadable data.

### Architecture Components

| Component | Responsibility |
|---|---|
| `data_loader.py` | Data ingestion, validation, parsing, and caching |
| `app.py` | Application initialization, filtering workflow, and module dispatch |
| `kpi_engine.py` | Vectorized computation across five KPI domains |
| `analytics.py` | Reusable statistical and analytical functions |
| `components.py` | Shared UI components, filters, and CSV exports |
| `modules/` | Four independent analytical dashboard modules |

The architecture separates data ingestion, application logic, KPI computation, analytical processing, and presentation. This modular design supports code reusability, maintainability, and independent development of analytical dashboard modules.

## Core Features and Analytical Modules

The project provides an interactive analytics dashboard for examining manufacturing process health, operational performance, telemetry reliability, and production efficiency.

### Core Features

- **Interactive Data Filtering:** Filter manufacturing records by machine ID, operation mode, and date range.
- **Manufacturing KPI Computation:** Calculate performance indicators across machine health, production throughput, product quality, network reliability, and energy efficiency.
- **Machine Health Monitoring:** Examine machine temperature, vibration, and performance-related indicators.
- **Production and Energy Analysis:** Analyze production speed, power consumption, and specific energy consumption across operating conditions.
- **Quality Assessment:** Examine defect-related indicators and quality performance across machines and operating modes.
- **Network Reliability Analysis:** Explore network latency and packet-loss distributions using statistical summaries and empirical cumulative distribution functions (ECDF).
- **Statistical Anomaly Screening:** Apply Mahalanobis distance-based screening to identify observations with unusual multivariate characteristics.
- **Interactive Visualizations:** Explore analytical results through interactive charts, KPI cards, and summary tables.
- **Data Export:** Download supported analytical results and filtered data as CSV files.

### Analytical Dashboard Modules

#### 1. Factory Health and Network Overview

Provides a consolidated view of manufacturing process health and telemetry network performance. It combines high-level KPI indicators with machine and network summaries to help users examine overall operational conditions.

#### 2. Machine Health and Condition Monitoring

Focuses on machine-level condition indicators, including temperature, vibration, and related health measurements. It supports machine-wise comparisons and statistical screening of unusual observations.

#### 3. Production Throughput and Energy Monitoring

Examines production performance across machines and operating modes. It includes production speed, power consumption, and specific energy consumption analysis to support comparisons of operational and energy performance.

#### 4. Quality Assurance and Efficiency Diagnostics

Examines quality-related indicators, including defects and errors, alongside operational efficiency measurements. It supports comparisons across machines and operating conditions to identify areas requiring further investigation.

The four modules are accessible through the Streamlit application. Each module uses the filtered manufacturing dataset and relevant KPI results, with shared analytical functions and reusable interface components.

## Analytical Methodology

The analytical methodology combines descriptive statistics, KPI computation, distribution analysis, and multivariate screening to evaluate manufacturing process performance.

### Analytical Workflow

```mermaid
flowchart TB

    A["Filtered Manufacturing Dataset"]

    B["Data Preparation<br/>Validated Records · Parsed Timestamps<br/>Machine and Operation Mode Filters"]

    C["KPI Computation<br/>Machine Health · Production<br/>Quality · Network · Energy"]

    D{"Analytical Processing"}

    M["Machine Health Analysis<br/>Temperature · Vibration<br/>Mahalanobis Distance Screening"]

    N["Network Reliability Analysis<br/>Latency · Packet Loss<br/>ECDF · Latency Dispersion"]

    P["Production and Energy Analysis<br/>Production Speed · Power<br/>Specific Energy Consumption"]

    Q["Quality and Efficiency Analysis<br/>Defect and Error Indicators<br/>Operational Comparisons"]

    R["Analytical Results<br/>Statistical Summaries · KPI Indicators<br/>Distribution Patterns · Unusual Observations"]

    S["Interactive Dashboard Presentation<br/>Charts · Tables · KPI Cards · CSV Exports"]

    A --> B --> C --> D

    D --> M
    D --> N
    D --> P
    D --> Q

    M --> R
    N --> R
    P --> R
    Q --> R

    R --> S

    classDef input fill:#0B3562,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef process fill:#102F52,stroke:#3B82F6,color:#FFFFFF,stroke-width:1.5px;
    classDef analysis fill:#123B60,stroke:#60A5FA,color:#FFFFFF,stroke-width:1.5px;
    classDef decision fill:#164E8A,stroke:#60A5FA,color:#FFFFFF,stroke-width:2px;
    classDef output fill:#164E8A,stroke:#60A5FA,color:#FFFFFF,stroke-width:2.5px;

    class A input;
    class B,C process;
    class D decision;
    class M,N,P,Q analysis;
    class R,S output;

    linkStyle default stroke:#3B82F6,stroke-width:2px;
```

### Key Analytical Techniques

| Technique | Application |
|---|---|
| Descriptive Statistics | Summarizing machine, production, and operational measurements |
| KPI Computation | Evaluating five manufacturing performance domains |
| Empirical Cumulative Distribution Function (ECDF) | Examining network latency distributions |
| Mahalanobis Distance | Screening observations with unusual multivariate characteristics |
| Comparative Analysis | Evaluating performance across machines and operating modes |
| Energy Efficiency Analysis | Examining power consumption and specific energy consumption |

**Implementation:** `kpi_engine.py` handles KPI computation, while `analytics.py` provides reusable statistical and analytical functions.

**Interpretation:** The methodology supports descriptive performance assessment and anomaly screening. Mahalanobis screening identifies statistically unusual observations; it does not independently establish equipment failure or predict future breakdowns. Latency dispersion is treated as a statistical proxy, not a direct measurement of network packet jitter.

## Dataset Overview

The project uses a manufacturing telemetry dataset stored in CSV format. The dataset contains machine-level and operational measurements used for manufacturing health, production, quality, network, and energy-efficiency analysis.

### Dataset at a Glance

```mermaid
flowchart TB

    A["Manufacturing Telemetry Dataset<br/>Thales_Group_Manufacturing.csv"]

    A --> B["100,000<br/>Records"]
    A --> C["14<br/>Columns"]
    A --> D["50<br/>Machines"]
    A --> E["Jan 01 – Mar 10, 2025<br/>69 Calendar Dates"]

    A --> F["Data Quality Audit<br/>No Missing Values Reported"]

    classDef dataset fill:#0B3562,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef metric fill:#102F52,stroke:#60A5FA,color:#FFFFFF,stroke-width:1.5px;

    class A dataset;
    class B,C,D,E,F metric;

    linkStyle default stroke:#3B82F6,stroke-width:2px;
```

### Dataset Summary

| Attribute | Description |
|---|---|
| File | `Thales_Group_Manufacturing.csv` |
| Format | CSV |
| Total Records | 100,000 |
| Total Columns | 14 |
| Machine Coverage | 50 machines |
| Recorded Period | January 1 – March 10, 2025 |
| Missing Values | None reported in the dataset audit |

### Data Utilization

The dataset supports the following analytical domains:

- Machine health and condition monitoring
- Production throughput and operational performance
- Product quality assessment
- Network reliability analysis
- Energy consumption and efficiency analysis

### Data Provenance and Limitations

The dataset is included in the project repository as a manufacturing telemetry CSV. Its original provenance and collection methodology have not been independently established. Therefore, the filename alone should not be interpreted as verification that the data was directly collected or supplied by Thales Group.

The observed data characteristics also warrant caution when interpreting the dataset as real-world factory telemetry. Results presented by the dashboard should be understood as analyses of the provided dataset, not as independently validated measurements of an operational manufacturing facility.


## Technology Stack

The project is implemented using Python-based data processing and analytical libraries, with Streamlit providing the interactive dashboard interface.

### Technology Overview

```mermaid
flowchart TB

    A["Smart Factory Analytics Application"]

    A --> B["Application Layer"]
    A --> C["Data Processing Layer"]
    A --> D["Analytics and Visualization"]
    A --> E["Data and Testing"]

    B --> B1["Python"]
    B --> B2["Streamlit"]

    C --> C1["Pandas"]
    C --> C2["NumPy"]

    D --> D1["SciPy"]
    D --> D2["Plotly"]

    E --> E1["CSV Dataset"]
    E --> E2["Pytest"]

    classDef main fill:#0B3562,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef tech fill:#102F52,stroke:#60A5FA,color:#FFFFFF,stroke-width:1.5px;

    class A main;
    class B,C,D,E,B1,B2,C1,C2,D1,D2,E1,E2 tech;

    linkStyle default stroke:#3B82F6,stroke-width:2px;
```

### Technology Reference

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Interactive web application and dashboard |
| Pandas | Dataset loading, manipulation, and filtering |
| NumPy | Numerical and vectorized computations |
| SciPy | Statistical and scientific computations |
| Plotly | Interactive data visualizations |
| CSV | Manufacturing telemetry data storage |
| Pytest | Automated testing |

**Dependency Management:** Project dependencies are specified in `requirements.txt`.

## Project Directory Structure

The repository is organized into separate directories for application logic, manufacturing data, analytical modules, reports, and automated tests.

```text
smart-factory-manufacturing-analytics/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   └── raw/
│       └── Thales_Group_Manufacturing.csv
│
├── scripts/
│   └── app/
│       ├── data_loader.py
│       ├── kpi_engine.py
│       ├── analytics.py
│       ├── components.py
│       │
│       └── modules/
│           ├── factory_overview.py
│           ├── machine_health.py
│           ├── production_energy.py
│           └── quality_efficiency.py
│
├── reports/
│   ├── audit/
│   │   └── figures/
│   │
│   └── research/
│       ├── 02_ieee_manuscript_draft.pdf
│       ├── 02_ieee_manuscript_draft.tex
│       └── 02_ieee_references.bib
│
├── build/
│   └── research/
│       └── IEEE_Manuscript_Overleaf.zip
│
└── tests/
    └── test files
```

### Directory Responsibilities

| Directory / File | Purpose |
|---|---|
| `app.py` | Main Streamlit application entry point |
| `data/raw/` | Source manufacturing telemetry dataset |
| `scripts/app/` | Data processing, KPI computation, analytics, and UI utilities |
| `scripts/app/modules/` | Four independent analytical dashboard modules |
| `reports/audit/` | Dataset audit reports and supporting figures |
| `reports/research/` | Research manuscript and bibliography |
| `build/research/` | Packaged research manuscript files |
| `tests/` | Automated project tests |
| `requirements.txt` | Python dependency definitions |

## Testing and Validation

The project includes a dedicated testing structure to support verification of application functionality and analytical components.

### Validation Areas

| Area | Validation Focus |
|---|---|
| Data Loading | Dataset accessibility and loading |
| Data Processing | Data filtering and transformation |
| KPI Computation | Correctness of calculated performance indicators |
| Analytical Functions | Statistical computation and analytical outputs |
| Dashboard Modules | Integration of analytical results with dashboard components |

### Automated Testing

The repository includes a `tests/` directory for automated test cases.

Run the test suite using:

```bash
pytest
```

Testing helps identify implementation issues and improves the reliability and maintainability of the analytical application.


## Research Manuscript

The project is accompanied by a research manuscript titled:

**Manufacturing Process Health and Operational Efficiency Analysis: A Data-Driven Framework for 6G-Oriented Smart Factories**

The manuscript presents the analytical framework, methodology, experimental observations, and findings associated with the project.

### Research Resources

| Resource | Link |
|---|---|
| Research Manuscript (PDF) | [View PDF](reports/research/02_ieee_manuscript_draft.pdf) |
| LaTeX Source | [View Source](reports/research/02_ieee_manuscript_draft.tex) |
| References | [View Bibliography](reports/research/02_ieee_references.bib) |
| Overleaf Project Package | [View ZIP](build/research/IEEE_Manuscript_Overleaf.zip) |

> **Publication Status:** This manuscript is available as a research working paper. It has not yet undergone peer review or formal journal publication.



## Limitations and Future Scope

### Current Limitations

The current implementation has the following limitations:

- **Dataset Provenance:** The original source and collection methodology of the manufacturing dataset have not been independently verified.
- **Dataset Dependency:** The dashboard currently relies on the provided CSV dataset rather than a live industrial data stream.
- **Network Representation:** Network reliability analysis uses the available latency and packet-loss measurements; it does not represent a deployed 5G or 6G communication infrastructure.
- **Statistical Screening:** Mahalanobis distance identifies unusual multivariate observations but does not confirm equipment failure or predict future breakdowns.
- **Predictive Capability:** The current application primarily provides descriptive and diagnostic analytics rather than a validated predictive maintenance system.
- **Deployment Environment:** The public dashboard is hosted on Streamlit Community Cloud and may hibernate during periods of inactivity.

### Future Scope

The framework can be extended through the following development directions:

```mermaid id="fut6g"
flowchart LR

    A["Current Analytics Framework"]

    A --> B["Industrial Data Integration<br/>Real-Time Sensor and IIoT Data"]

    A --> C["Advanced Predictive Analytics<br/>Validated Machine Learning Models"]

    A --> D["6G-Oriented Network Evaluation<br/>Real Network KPIs and QoS Analysis"]

    A --> E["Scalable Deployment<br/>Continuous Data Processing<br/>Production-Ready Infrastructure"]

    B --> F["Future Smart Factory<br/>Intelligence Framework"]
    C --> F
    D --> F
    E --> F

    classDef current fill:#0B3562,stroke:#3B82F6,color:#FFFFFF,stroke-width:2px;
    classDef future fill:#102F52,stroke:#60A5FA,color:#FFFFFF,stroke-width:1.5px;
    classDef target fill:#164E8A,stroke:#60A5FA,color:#FFFFFF,stroke-width:2.5px;

    class A current;
    class B,C,D,E future;
    class F target;

    linkStyle default stroke:#3B82F6,stroke-width:2px;
```

Potential extensions include integrating verified industrial sensor datasets, developing and validating predictive maintenance models, evaluating real network quality-of-service measurements, and implementing scalable continuous data-processing infrastructure.


## Author and Contact

**Nitin Sharma**  
Undergraduate Student  
Department of Computer Science and Engineering (AI & ML)  
VIT Bhopal University  
Kothrikalan, Sehore – 466114  
Madhya Pradesh, India

**Email:** nitin.25bai11122@vitbhopal.ac.in

**GitHub:** [nitin25J](https://github.com/nitin25J)

**Project Repository:** [Smart Factory Manufacturing Analytics](https://github.com/nitin25J/smart-factory-manufacturing-analytics)

**Live Application:** [Open Streamlit Dashboard](https://smart-factory-manufacturing-analytics-tjambjpnvyme6cdqysgqvp.streamlit.app/)

---

*Developed as an academic and research-oriented project exploring data-driven manufacturing process health and operational efficiency analysis for 6G-oriented smart factories.*

These directions represent proposed future work and are not claimed as existing capabilities of the current application.
