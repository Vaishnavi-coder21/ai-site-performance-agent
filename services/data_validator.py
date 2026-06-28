import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DataValidator:
    """
    A modular data validation engine to generate a Data Quality Report.
    """
    def __init__(self, data_pipeline_output: Dict[str, pd.DataFrame]):
        self.data = data_pipeline_output
        self.quality_issues: List[Dict[str, Any]] = []

    def _add_issue(self, issue_type: str, row_idx: Any, column: str, description: str, severity: str, suggested_fix: str):
        self.quality_issues.append({
            "Issue Type": issue_type,
            "Affected Row": row_idx,
            "Column": column,
            "Description": description,
            "Severity": severity,
            "Suggested Fix": suggested_fix
        })

    def validate(self) -> pd.DataFrame:
        logger.info("Starting comprehensive data validation...")
        
        # Deduplicate column names per DataFrame before validation
        clean_data = {}
        for name, df in self.data.items():
            if df.columns.duplicated().any():
                logger.warning(f"[{name}] Duplicate column names found — deduplicating.")
                df = df.loc[:, ~df.columns.duplicated()]
            clean_data[name] = df
        self.data = clean_data

        self.check_missing_values()
        self.check_duplicate_records()
        self.check_negative_values()
        self.check_invalid_dates()
        
        if 'sales' in self.data:
            self.check_missing_owner(self.data['sales'])
        
        if 'construction' in self.data:
            self.check_blank_delay_reason(self.data['construction'])
            
        self.check_cross_file_consistency()
        
        logger.info(f"Validation complete. Found {len(self.quality_issues)} issues.")
        return pd.DataFrame(self.quality_issues)

    def check_missing_values(self):
        for df_name, df in self.data.items():
            for col in df.columns:
                missing_rows = df[df[col].isna() | (df[col] == "")]
                for idx in missing_rows.index:
                    self._add_issue(
                        "Missing Value", idx, f"{df_name}.{col}", 
                        f"Value is missing or empty in {df_name} data.", 
                        "Medium", "Provide the missing value."
                    )

    def check_duplicate_records(self):
        for df_name, df in self.data.items():
            try:
                duplicates = df[df.duplicated(keep=False)]
                for idx in duplicates.index:
                    self._add_issue(
                        "Duplicate Record", idx, f"{df_name}.(All)", 
                        f"Row is an exact duplicate in {df_name} data.", 
                        "High", "Remove duplicate entry."
                    )
            except Exception as e:
                logger.warning(f"Could not check duplicates for {df_name}: {e}")

    def check_negative_values(self):
        for df_name, df in self.data.items():
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                negatives = df[df[col] < 0]
                for idx in negatives.index:
                    self._add_issue(
                        "Negative Value", idx, f"{df_name}.{col}", 
                        f"Found negative numeric value: {df.at[idx, col]}.", 
                        "High", "Verify if the value should be absolute or correct the data entry."
                    )

    def check_invalid_dates(self):
        date_keywords = ['date', 'month']
        for df_name, df in self.data.items():
            for col in df.columns:
                if any(kw in col.lower() for kw in date_keywords):
                    # Check if it can be converted to datetime
                    for idx, val in df[col].items():
                        if pd.notna(val):
                            try:
                                pd.to_datetime(val)
                            except Exception:
                                self._add_issue(
                                    "Invalid Date", idx, f"{df_name}.{col}", 
                                    f"Value '{val}' cannot be parsed as a date.", 
                                    "High", "Ensure standard date formatting (e.g., YYYY-MM-DD)."
                                )

    def check_missing_owner(self, sales_df: pd.DataFrame):
        owner_col = next((col for col in sales_df.columns if 'owner' in col.lower()), None)
        if owner_col:
            missing_owners = sales_df[sales_df[owner_col].isna() | (sales_df[owner_col] == "")]
            for idx in missing_owners.index:
                self._add_issue(
                    "Missing Owner", idx, f"sales.{owner_col}", 
                    "Sales record has no assigned owner.", 
                    "High", "Assign a valid Sales Owner."
                )

    def check_blank_delay_reason(self, const_df: pd.DataFrame):
        # Infer delay column and reason column
        delay_col = next((col for col in const_df.columns if 'delay' in col.lower() and 'reason' not in col.lower()), None)
        reason_col = next((col for col in const_df.columns if 'reason' in col.lower()), None)
        
        if delay_col and reason_col:
            # Assumes delay is a numeric > 0 or a string indicating delay
            for idx, row in const_df.iterrows():
                try:
                    is_delayed = float(row[delay_col]) > 0
                except (ValueError, TypeError):
                    is_delayed = str(row[delay_col]).strip().lower() in ['yes', 'true', 'delayed']
                
                if is_delayed and pd.isna(row[reason_col]):
                    self._add_issue(
                        "Blank Delay Reason", idx, f"construction.{reason_col}", 
                        f"Milestone is delayed but no reason is provided.", 
                        "Medium", "Provide a detailed delay reason."
                    )

    def check_cross_file_consistency(self):
        sales_df = self.data.get('sales')
        const_df = self.data.get('construction')
        col_df = self.data.get('collections')
        
        if sales_df is None: return
        
        sales_projects = set(sales_df['Project'].dropna().unique()) if 'Project' in sales_df.columns else set()
        sales_towers = set(sales_df['Tower'].dropna().unique()) if 'Tower' in sales_df.columns else set()
        sales_customers = set(sales_df['Customer Code'].dropna().unique()) if 'Customer Code' in sales_df.columns else set()
        
        # Check Construction vs Sales (Projects & Towers)
        if const_df is not None:
            if 'Project' in const_df.columns:
                for idx, val in const_df['Project'].items():
                    if pd.notna(val) and val not in sales_projects:
                        self._add_issue("Wrong Project", idx, "construction.Project", f"Project '{val}' not found in Sales baseline.", "High", "Correct project name or update baseline.")
            
            if 'Tower' in const_df.columns:
                for idx, val in const_df['Tower'].items():
                    if pd.notna(val) and val not in sales_towers:
                        self._add_issue("Wrong Tower", idx, "construction.Tower", f"Tower '{val}' not found in Sales baseline.", "High", "Correct tower name or update baseline.")

        # Check Collections vs Sales (Customer Code)
        if col_df is not None:
            if 'Customer Code' in col_df.columns:
                for idx, val in col_df['Customer Code'].items():
                    if pd.notna(val) and val not in sales_customers:
                        self._add_issue("Wrong Customer Code", idx, "collections.Customer Code", f"Customer '{val}' not found in Sales baseline.", "High", "Verify customer code against sales master.")
