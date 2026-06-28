# Architecture Note: Real Estate AI Agent

## 1. Executive Summary
This document outlines the architecture for the **AI Site Performance & Cash Flow Agent**. The solution marries deterministic data processing (Pandas) with generative AI synthesis (LangGraph + OpenAI) to produce a highly reliable, zero-hallucination enterprise reporting workflow.

## 2. Process Flow & Architecture Diagram

```mermaid
graph TD
    subgraph Data Ingestion Layer
        A1[Sales.xlsx] --> B(Data Loader)
        A2[Construction.xlsx] --> B
        A3[Collections.xlsx] --> B
        A4[AOP_Targets.xlsx] --> B
    end

    subgraph Processing & Validation Layer
        B --> C{Data Validator}
        C -- Missing/Corrupt --> C1[Data Quality Report]
        C -- Clean Data --> D(Data Linking Engine)
        D -- Orphan Records --> D1[Unmatched Report]
        D -- Outer Joins --> D2[(Master DataFrame)]
    end

    subgraph Business Rules Engine (Deterministic)
        D2 --> E1[Sales Rule < 80%]
        D2 --> E2[Collection Rule < 85%]
        D2 --> E3[Overdue > 30 Days]
        D2 --> E4[Cost Overrun > 10%]
        D2 --> E5[Cross-Functional Escalation]
        E1 & E2 & E3 & E4 & E5 --> F[Action Items DataFrame]
    end

    subgraph AI Synthesis Layer (LangGraph)
        F --> G1(Sales Agent)
        F --> G2(Collections Agent)
        F --> G3(Construction Agent)
        F --> G4(Risk Agent)
        
        G1 & G2 & G3 & G4 --> H1(Communication Agent)
        H1 --> H2(Report Agent)
        
        H2 --> I1[Leadership Report]
        H2 --> I2[Draft Communications]
    end

    subgraph Presentation Layer (Streamlit)
        C1 & D1 & F & I1 & I2 --> J[Executive UI Dashboard]
        J --> K[Monthly Site Review Package Excel]
    end
```

## 3. Core Components

### 3.1 Data Loader (`services/data_loader.py`)
*   **Ingestion**: Dynamically detects worksheets. Does not rely on hardcoded sheet names.
*   **Validation**: Uses Pydantic schemas to ensure all required columns exist before processing.

### 3.2 Data Linking Engine (`services/data_linker.py`)
*   **Mechanism**: Performs robust `outer` joins tracking `_merge` indicators.
*   **Safety**: Guaranteeing zero silent data loss. Any unmatched records are logged to the Unmatched Report.

### 3.3 Business Rules Engine (`services/rules_engine.py`)
*   **Method**: 100% Python/Pandas deterministic logic.
*   **Why**: Calculations (sums, variances, day differences) must be precise. LLMs are not used for math.

### 3.4 AI Workflow (`agents/workflow.py`)
*   **Orchestration**: LangGraph coordinates the agent sequence.
*   **Guardrails**: Prompts explicitly forbid math. The LLM only receives pre-calculated `action_items` as JSON to synthesize insights and draft emails.

## 4. Human-in-the-Loop 
*   Communications are generated as **Drafts**, never sent automatically.
*   Data mismatches and missing values are flagged to the user via the UI rather than automatically imputed, ensuring data integrity remains in human hands.
