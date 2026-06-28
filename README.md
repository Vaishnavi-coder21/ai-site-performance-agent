# AI Site Performance & Cash Flow Agent

A production-ready AI solution that automates real estate month-end site performance reviews. This robust pipeline ingests raw operational Excel data, applies deterministic business rules, securely merges disparate datasets, and leverages a multi-agent LangGraph workflow to generate executive-ready insights.

## Features
- **Streamlit Dashboard**: A fully responsive, modern UI with interactive KPI cards and Plotly charts.
- **Robust Data Ingestion**: Dynamically parses worksheets, validates column schemas via Pydantic, and handles corrupted files securely.
- **Data Quality Engine**: Scans for missing values, cross-file orphans, duplicate records, and invalid data types.
- **Zero-Loss Data Linking**: Implements strict Pandas outer joins to ensure no records are silently dropped, generating an "Unmatched Record" report for data governance.
- **Deterministic Business Rules**: 100% Python-based calculations for sales targets, construction delays, cash flow leakage, and cross-functional escalations.
- **LangGraph Multi-Agent Synthesis**: An AI orchestrator featuring specialized agents (Sales, Collections, Construction, Risk, Communication, Report) that strictly analyze pre-calculated deviations.
- **Professional Reporting**: Generates a richly formatted, multi-sheet Excel workbook complete with native charts and conditional styling using `openpyxl`.

## System Requirements
- Python 3.12+
- OpenAI API Key

## Setup & Installation

1. **Clone or Navigate to the Directory**
   ```bash
   cd real_estate_agent
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Ensure your `.env` file contains your OpenAI API Key. You can copy the template:
   ```bash
   cp .env.example .env
   # Add your key to .env: OPENAI_API_KEY=sk-xxxx
   ```

## Running the Application

Launch the interactive dashboard by running:
```bash
streamlit run app.py
```

Then, simply upload your four source Excel files:
1. `Sales_SANITIZED.xlsx`
2. `Construction_Tracking.xlsx`
3. `Collections_Tracker.xlsx`
4. `AOP_Targets.xlsx`

Click **Analyze & Generate Dashboard**.

## Architecture Highlights
* **Python/Pandas**: Used exclusively for mathematical calculations to eliminate LLM hallucinations.
* **LangGraph**: Orchestrates the multi-agent AI flow sequentially.
* **OpenAI (GPT-4o)**: Used strictly for drafting human-readable emails and synthesizing insights based *only* on the deterministic data outputs.

*Please refer to `Architecture_Note.md` and `Process_Note.md` for deeper technical workflow details.*
