import pandas as pd
from typing import List, Dict, Any

class BaseRule:
    """Base class for all business rules."""
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        raise NotImplementedError("Each rule must implement the evaluate method.")

    def create_result(self, status: str, reason: str, recommendation: str, owner: str, severity: str, affected_records: Any) -> Dict[str, Any]:
        return {
            "Status": status,
            "Reason": reason,
            "Recommendation": recommendation,
            "Owner": owner,
            "Severity": severity,
            "Affected Records": affected_records
        }

class SalesTargetRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        sales_df = data.get('sales')
        aop_df = data.get('aop')
        
        if sales_df is None or aop_df is None: return results
        if 'Booking Value' not in sales_df.columns or 'Value' not in aop_df.columns: return results
        
        # Calculate actual sales by Project
        actual_sales = sales_df.groupby('Project')['Booking Value'].sum().reset_index()
        target_sales = aop_df[aop_df['Target Type'].str.lower() == 'sales target'] if 'Target Type' in aop_df.columns else pd.DataFrame()
        
        if target_sales.empty: return results
        target_sales = target_sales.groupby('Project')['Value'].sum().reset_index()
        
        merged = pd.merge(actual_sales, target_sales, on='Project', suffixes=('_actual', '_target'))
        for _, row in merged.iterrows():
            if row['Value'] > 0 and (row['Booking Value'] / row['Value']) < 0.80:
                results.append(self.create_result(
                    "Sales Risk", f"Sales for {row['Project']} is below 80% of target.",
                    "Review pricing strategy and marketing pipeline.", "Sales Head", "High", row['Project']
                ))
        return results

class CollectionTargetRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        col_df = data.get('collections')
        aop_df = data.get('aop')
        if col_df is None or aop_df is None: return results
        
        if 'Amount Collected' in col_df.columns and 'Value' in aop_df.columns:
            actual_col = col_df['Amount Collected'].sum()
            target_col = aop_df[aop_df['Target Type'].str.lower() == 'collections target']['Value'].sum()
            if target_col > 0 and (actual_col / target_col) < 0.85:
                results.append(self.create_result(
                    "Collections Risk", "Total collections below 85% of target.",
                    "Intensify follow-ups on due demands.", "Collections Head", "High", "All"
                ))
        return results

class OverdueCollectionRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        col_df = data.get('collections')
        if col_df is None: return results
        
        overdue_col = next((c for c in col_df.columns if 'overdue' in c.lower() and 'days' in c.lower()), None)
        if overdue_col:
            overdues = col_df[pd.to_numeric(col_df[overdue_col], errors='coerce') > 30]
            for _, row in overdues.iterrows():
                results.append(self.create_result(
                    "Collection Priority", f"Customer {row.get('Customer Code', 'Unknown')} overdue by >30 days.",
                    "Issue final notice and escalate to legal if necessary.", "Collections Manager", "High", row.get('Customer Code')
                ))
        return results

class ConstructionDelayRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        const_df = data.get('construction')
        if const_df is None: return results
        
        delay_col = next((c for c in const_df.columns if 'delay' in c.lower() and 'reason' not in c.lower()), None)
        if delay_col:
            delays = const_df[pd.to_numeric(const_df[delay_col], errors='coerce') > 15]
            for _, row in delays.iterrows():
                results.append(self.create_result(
                    "Construction Risk", f"Milestone '{row.get('Milestone')}' delayed by >15 days.",
                    "Expedite resources or revise schedule.", "Construction Head", "High", f"{row.get('Project')} - {row.get('Tower')}"
                ))
        return results

class PendingPaymentRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        # Construction completed but payment pending
        if 'Actual Progress' in master_df.columns and 'Demand Raised' in master_df.columns and 'Amount Collected' in master_df.columns:
            try:
                # Guard against duplicate column names from outer join returning a DataFrame
                def safe_series(df, col):
                    s = df[col]
                    if isinstance(s, pd.DataFrame):
                        s = s.iloc[:, 0]
                    return s

                completed = master_df[safe_series(master_df, 'Actual Progress').astype(str).str.lower().isin(['100%', 'completed', 'done', '100'])]
                demand = pd.to_numeric(safe_series(completed, 'Demand Raised'), errors='coerce')
                collected = pd.to_numeric(safe_series(completed, 'Amount Collected'), errors='coerce')
                leakage = completed[demand > collected]
                for _, row in leakage.iterrows():
                    results.append(self.create_result(
                        "Cash Flow Leakage", f"Milestone achieved but payment pending for customer {row.get('Customer Code')}.",
                        "Raise immediate demand note and follow up.", "Collections Head", "High", row.get('Customer Code')
                    ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"PendingPaymentRule skipped: {e}")
        return results

class CostOverrunRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        const_df = data.get('construction')
        aop_df = data.get('aop')
        if const_df is None or aop_df is None: return results
        
        if 'Cost Impact' in const_df.columns:
            overruns = const_df[pd.to_numeric(const_df['Cost Impact'], errors='coerce') > 0] # Assuming Cost Impact represents the overrun amount
            # Alternatively, if actual cost > 1.1 * target cost
            for _, row in overruns.iterrows():
                results.append(self.create_result(
                    "Cost Overrun", f"Cost overrun detected for milestone '{row.get('Milestone')}'.",
                    "Audit material and labor expenses.", "Finance Head", "High", f"{row.get('Project')} - {row.get('Tower')}"
                ))
        return results

class ProductMixRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        sales_df = data.get('sales')
        aop_df = data.get('aop')
        if sales_df is None or aop_df is None: return results
        
        unit_type_col = next((c for c in sales_df.columns if 'type' in c.lower() or 'details' in c.lower()), None)
        if unit_type_col:
            actual_mix = sales_df[unit_type_col].value_counts()
            # Simplistic check: If an AOP target for product mix exists, compare.
            results.append(self.create_result(
                "Product Mix Insight", "Evaluated actual product mix.",
                "Align future marketing with slow-moving inventory.", "Sales Head", "Medium", str(actual_mix.to_dict())
            ))
        return results

class CashFlowRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        col_df = data.get('collections')
        const_df = data.get('construction')
        
        inflow = pd.to_numeric(col_df['Amount Collected'], errors='coerce').sum() if col_df is not None and 'Amount Collected' in col_df.columns else 0
        outflow = pd.to_numeric(const_df['Cost Impact'], errors='coerce').sum() if const_df is not None and 'Cost Impact' in const_df.columns else 0 # Simplified outflow
        
        ncf = inflow - outflow
        results.append(self.create_result(
            "Cash Flow Update", f"Net Cash Flow is {ncf}.",
            "Maintain liquidity reserves.", "Leadership", "Low" if ncf > 0 else "High", "All"
        ))
        return results

class CrossFunctionalEscalationRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        # This would require accessing the results of previous rules.
        # Implemented inside the Engine itself by analyzing aggregated rule results.
        return []

class ClarificationRule(BaseRule):
    def evaluate(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        results = []
        const_df = data.get('construction')
        if const_df is None: return results
        
        delay_col = next((c for c in const_df.columns if 'delay' in c.lower() and 'reason' not in c.lower()), None)
        reason_col = next((c for c in const_df.columns if 'reason' in c.lower()), None)
        
        if delay_col and reason_col:
            delayed_no_reason = const_df[(pd.to_numeric(const_df[delay_col], errors='coerce') > 0) & (const_df[reason_col].isna() | (const_df[reason_col] == ""))]
            for _, row in delayed_no_reason.iterrows():
                results.append(self.create_result(
                    "Clarification Required", f"Delay reason missing for milestone '{row.get('Milestone')}'.",
                    "Site Manager to provide official reason for delay.", "Site Manager", "Medium", f"{row.get('Project')} - {row.get('Tower')}"
                ))
        return results

class BusinessRulesEngine:
    """Executes all business rules and aggregates results."""
    def __init__(self):
        self.rules: List[BaseRule] = [
            SalesTargetRule(),
            CollectionTargetRule(),
            OverdueCollectionRule(),
            ConstructionDelayRule(),
            PendingPaymentRule(),
            CostOverrunRule(),
            ProductMixRule(),
            CashFlowRule(),
            ClarificationRule()
        ]
        self.escalation_rule = CrossFunctionalEscalationRule()

    def run_all(self, master_df: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        all_results = []
        for rule in self.rules:
            all_results.extend(rule.evaluate(master_df, data))
            
        # Cross Functional Escalation Logic
        project_risks = {}
        for res in all_results:
            if 'Project' in str(res['Affected Records']) or (res['Status'] in ["Sales Risk", "Construction Risk"]):
                proj = str(res['Affected Records']).split(" - ")[0]
                if proj not in project_risks:
                    project_risks[proj] = set()
                project_risks[proj].add(res['Status'])
                
        for proj, risks in project_risks.items():
            if "Sales Risk" in risks and ("Construction Risk" in risks or "Collections Risk" in risks):
                all_results.append(self.escalation_rule.create_result(
                    "Cross-Functional Escalation", f"Project {proj} has simultaneous Sales and execution risks.",
                    "Require joint committee review.", "Leadership", "Critical", proj
                ))

        return pd.DataFrame(all_results)
