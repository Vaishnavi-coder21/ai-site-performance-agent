# Process Note: Real Estate AI Agent

## 1. Setup Steps
1. Ensure Python 3.9+ is installed.
2. Install dependencies using: `pip install -r requirements.txt` (requires pandas, openpyxl, openai).
3. Place the 4 input Excel files in the same directory as the script.
4. Run `python main.py` to execute the data pipeline.

## 2. Tools Used
*   **Python & Pandas**: For deterministic, formula-driven calculations and joining disparate datasets.
*   **LLMs / Generative AI**: For synthesizing numerical deviations into human-readable action plans and draft communications.
*   **Openpyxl**: For reading/writing Excel reporting files.

## 3. Assumptions and Limitations
*   *Assumption*: The structure (column names) of the Excel files is generally consistent.
*   *Assumption*: Missing data points are highlighted rather than imputed.
*   *Limitation*: Communications are generated as drafts and not sent automatically.

## 4. Dependencies
*   Python 3.x
*   pandas
*   openpyxl
*   openai (optional, for LLM steps)
