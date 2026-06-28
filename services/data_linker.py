import pandas as pd
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class DataLinkingEngine:
    """
    Engine to merge multiple datasets securely without silently dropping rows.
    Validates relationships and generates a comprehensive mismatch report.
    """
    def __init__(self, data: Dict[str, pd.DataFrame]):
        # Create copies to avoid mutating original ingested frames
        self.sales = data.get('sales', pd.DataFrame()).copy()
        self.construction = data.get('construction', pd.DataFrame()).copy()
        self.collections = data.get('collections', pd.DataFrame()).copy()
        self.aop = data.get('aop', pd.DataFrame()).copy()
        
        self.unmatched_records = []

    def _log_mismatches(self, merged_df: pd.DataFrame, left_name: str, right_name: str, merge_keys: list):
        """
        Extracts mismatched rows using the _merge indicator, logs them, 
        and appends them to the unmatched_records list.
        """
        if '_merge' not in merged_df.columns:
            return

        left_only = merged_df[merged_df['_merge'] == 'left_only']
        right_only = merged_df[merged_df['_merge'] == 'right_only']

        for _, row in left_only.iterrows():
            keys_info = {k: row.get(k) for k in merge_keys}
            msg = f"Record found in {left_name} but missing in {right_name} for keys {keys_info}"
            logger.warning(msg)
            self.unmatched_records.append({
                "Source": left_name,
                "Missing In": right_name,
                "Keys": str(keys_info),
                "Issue": "Unmatched left record"
            })

        for _, row in right_only.iterrows():
            keys_info = {k: row.get(k) for k in merge_keys}
            msg = f"Record found in {right_name} but missing in {left_name} for keys {keys_info}"
            logger.warning(msg)
            self.unmatched_records.append({
                "Source": right_name,
                "Missing In": left_name,
                "Keys": str(keys_info),
                "Issue": "Unmatched right record"
            })

    def generate_master_dataframe(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Executes a sequence of outer joins to construct a Master DataFrame.
        Captures and returns any orphan records.
        
        Returns:
            Tuple containing (master_dataframe, unmatched_report_dataframe)
        """
        logger.info("Starting Data Linking process...")

        # 1. Merge Sales and Collections
        # Common key: Customer Code
        sales_col_keys = ['Customer Code']
        if not self.sales.empty and not self.collections.empty:
            # Ensure keys exist
            available_keys = [k for k in sales_col_keys if k in self.sales.columns and k in self.collections.columns]
            if available_keys:
                master = pd.merge(self.sales, self.collections, on=available_keys, how='outer', indicator=True)
                self._log_mismatches(master, "Sales", "Collections", available_keys)
                master = master.drop(columns=['_merge'])
            else:
                logger.warning("No common keys found between Sales and Collections. Concatenating.")
                master = pd.concat([self.sales, self.collections], ignore_index=True)
        else:
            master = self.sales if not self.sales.empty else self.collections

        # 2. Merge with Construction
        # Common keys usually Project, Tower, Milestone
        const_keys = ['Project', 'Tower', 'Milestone']
        if not master.empty and not self.construction.empty:
            available_keys = [k for k in const_keys if k in master.columns and k in self.construction.columns]
            if available_keys:
                master = pd.merge(master, self.construction, on=available_keys, how='outer', indicator=True)
                self._log_mismatches(master, "Sales+Collections", "Construction", available_keys)
                master = master.drop(columns=['_merge'])
            else:
                logger.warning("No common keys found with Construction. Performing cross join or bypassing.")
                # We don't want a massive cross join, just keep columns
                for col in self.construction.columns:
                    if col not in master.columns:
                        master[col] = None
        
        # 3. Merge with AOP (Targets)
        # Common keys usually Month, Project, Target Type
        aop_keys = ['Month', 'Project']
        if not master.empty and not self.aop.empty:
            available_keys = [k for k in aop_keys if k in master.columns and k in self.aop.columns]
            if available_keys:
                master = pd.merge(master, self.aop, on=available_keys, how='outer', indicator=True)
                self._log_mismatches(master, "Master", "AOP", available_keys)
                master = master.drop(columns=['_merge'])
            else:
                logger.warning("No common keys found with AOP. Targets will remain unlinked.")
                
        logger.info(f"Data Linking complete. Master DataFrame shape: {master.shape}")
        
        unmatched_df = pd.DataFrame(self.unmatched_records)
        return master, unmatched_df
