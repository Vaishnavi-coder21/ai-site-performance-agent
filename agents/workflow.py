import os
import json
import logging
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
import openai

logger = logging.getLogger(__name__)

# State definition
class AgentState(TypedDict):
    action_items: List[Dict[str, Any]]
    sales_summary: str
    collections_summary: str
    construction_summary: str
    cash_flow_summary: str
    risk_summary: str
    communications: List[str]
    final_report: str

class AIGenerator:
    """Helper to call OpenAI API to generate text."""
    @staticmethod
    def generate(prompt: str, max_tokens: int = 800) -> str:
        # Check for GROQ API key first, then fallback to OPENAI API KEY for backward compatibility in our code
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # Also check Streamlit secrets if running in Streamlit
        if not api_key:
            try:
                import streamlit as st
                if "GROQ_API_KEY" in st.secrets:
                    api_key = st.secrets["GROQ_API_KEY"]
                elif "OPENAI_API_KEY" in st.secrets:
                    api_key = st.secrets["OPENAI_API_KEY"]
            except Exception:
                pass
        
        if not api_key or api_key == "your_openai_api_key_here" or api_key.startswith("sk-proj-k3o"):
            # Using the mock fallback if no valid key is present
            return f"*(AI Generation disabled due to missing or invalid API key)*\n\nBased on the data provided, the metrics have been successfully calculated. Please refer to the deterministic Action Items and Rules Engine output below for the exact performance deviations."
            
        try:
            # We use the OpenAI SDK but point it to Groq's free, blazing fast API!
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Groq's new free Llama 3.1 model
                messages=[
                    {"role": "system", "content": "You are a senior real estate business analyst and Chief of Staff. Synthesize structured data into highly professional, executive-ready insights. NEVER perform mathematical calculations. Only explain and contextualize the already calculated results provided to you."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return f"*(AI Generation disabled due to API limits/errors)*\n\nBased on the data provided, the metrics have been successfully calculated. Please refer to the deterministic Action Items and Rules Engine output below for the exact performance deviations."

# Node Functions

def sales_agent(state: AgentState) -> AgentState:
    sales_items = [item for item in state['action_items'] if item['Owner'] == 'Sales Head']
    if not sales_items:
        state['sales_summary'] = "Sales metrics are performing at or above targets. No critical deviations detected."
        return state
        
    prompt = f"Review these calculated sales deviations:\n{json.dumps(sales_items, indent=2)}\nProvide a professional Business Insight regarding sales performance and a short list of Recommended Actions."
    state['sales_summary'] = AIGenerator.generate(prompt)
    return state

def collections_agent(state: AgentState) -> AgentState:
    col_items = [item for item in state['action_items'] if 'Collection' in item['Owner']]
    if not col_items:
        state['collections_summary'] = "Collection metrics are performing at or above targets. No overdue risks detected."
        return state
        
    prompt = f"Review these calculated collection deviations:\n{json.dumps(col_items, indent=2)}\nProvide a professional Business Insight regarding collections and a short list of Recommended Actions."
    state['collections_summary'] = AIGenerator.generate(prompt)
    return state

def construction_agent(state: AgentState) -> AgentState:
    const_items = [item for item in state['action_items'] if 'Construction' in item['Owner'] or 'Site' in item['Owner']]
    if not const_items:
        state['construction_summary'] = "Construction milestones are on schedule. No cost overruns detected."
        return state
        
    prompt = f"Review these calculated construction deviations:\n{json.dumps(const_items, indent=2)}\nProvide a professional Business Insight regarding construction delays/costs and a short list of Recommended Actions."
    state['construction_summary'] = AIGenerator.generate(prompt)
    return state

def cash_flow_agent(state: AgentState) -> AgentState:
    cf_items = [item for item in state['action_items'] if 'Cash Flow' in item['Status']]
    if not cf_items:
        state['cash_flow_summary'] = "Cash flow is stable. Net cash flow calculations remain positive."
        return state
        
    prompt = f"Review these calculated cash flow alerts:\n{json.dumps(cf_items, indent=2)}\nProvide a professional Business Insight regarding liquidity and a short list of Recommended Actions."
    state['cash_flow_summary'] = AIGenerator.generate(prompt)
    return state

def risk_agent(state: AgentState) -> AgentState:
    risk_items = [item for item in state['action_items'] if item['Severity'] in ['High', 'Critical']]
    if not risk_items:
        state['risk_summary'] = "No critical systemic risks detected."
        return state
        
    prompt = f"Review these HIGH and CRITICAL severity calculated risks:\n{json.dumps(risk_items, indent=2)}\nProvide a detailed 'Risk Explanation' detailing why these specific escalations pose a threat to the project baseline."
    state['risk_summary'] = AIGenerator.generate(prompt)
    return state

def communication_agent(state: AgentState) -> AgentState:
    critical_items = [item for item in state['action_items'] if item['Severity'] == 'Critical']
    drafts = []
    
    if critical_items:
        prompt_teams = f"Draft an urgent, professional 'Teams Message' to the Leadership team escalating these pre-calculated critical risks. Do not calculate anything, just explain the data provided:\n{json.dumps(critical_items, indent=2)}"
        drafts.append("### Teams Message (Leadership Escalation)\n" + AIGenerator.generate(prompt_teams, 300))
        
    high_items = [item for item in state['action_items'] if item['Severity'] == 'High']
    if high_items:
        prompt_email = f"Draft a formal 'Email Draft' to the Department Heads addressing these pre-calculated high-priority issues. Request an immediate Owner-wise action plan based on these exact data points:\n{json.dumps(high_items, indent=2)}"
        drafts.append("### Email Draft (Department Heads)\n" + AIGenerator.generate(prompt_email, 400))
        
    if not drafts:
        drafts.append("No urgent Teams messages or Email drafts are required at this time.")
        
    state['communications'] = drafts
    return state

def report_agent(state: AgentState) -> AgentState:
    # Build Owner-wise action plan text from the raw data to ensure accuracy
    owner_plan_raw = {}
    for item in state['action_items']:
        owner = item.get('Owner', 'Unassigned')
        if owner not in owner_plan_raw:
            owner_plan_raw[owner] = []
        owner_plan_raw[owner].append(f"- [{item.get('Severity')}] {item.get('Status')}: {item.get('Reason')} -> {item.get('Recommendation')}")
    
    owner_plan_text = ""
    for owner, actions in owner_plan_raw.items():
        owner_plan_text += f"\n**{owner}**:\n" + "\n".join(actions)

    prompt = f"""
    You are finalizing the Month-End Leadership Review. 
    Using ONLY the pre-calculated insights provided below, generate a highly professional executive report.
    
    DO NOT perform any calculations. DO NOT invent new metrics.

    FORMAT REQUIRED:
    # Month-End Site Performance Review
    
    ## Leadership Summary
    (Synthesize the overall health of the site based on the insights below)
    
    ## Business Insights
    (Combine the departmental insights below into a cohesive narrative)
    
    ## Risk Explanation
    (Incorporate the Risk Agent's explanation here)
    
    ## Recommended Actions
    (Highlight the top strategic recommendations)
    
    ---
    DATA PROVIDED:
    Sales Insight: {state['sales_summary']}
    Collections Insight: {state['collections_summary']}
    Construction Insight: {state['construction_summary']}
    Cash Flow Insight: {state['cash_flow_summary']}
    Risk Explanation: {state['risk_summary']}
    """
    report_base = AIGenerator.generate(prompt, 1000)
    
    # We append the exact Owner-wise Action Plan directly to prevent LLM hallucination of the tasks
    state['final_report'] = report_base + "\n\n## Owner-wise Action Plan\n" + (owner_plan_text if owner_plan_text else "No pending actions.")
    
    return state

def build_workflow() -> StateGraph:
    """Builds and compiles the LangGraph workflow."""
    seq_workflow = StateGraph(AgentState)
    seq_workflow.add_node("sales_agent", sales_agent)
    seq_workflow.add_node("collections_agent", collections_agent)
    seq_workflow.add_node("construction_agent", construction_agent)
    seq_workflow.add_node("cash_flow_agent", cash_flow_agent)
    seq_workflow.add_node("risk_agent", risk_agent)
    seq_workflow.add_node("communication_agent", communication_agent)
    seq_workflow.add_node("report_agent", report_agent)
    
    seq_workflow.add_edge(START, "sales_agent")
    seq_workflow.add_edge("sales_agent", "collections_agent")
    seq_workflow.add_edge("collections_agent", "construction_agent")
    seq_workflow.add_edge("construction_agent", "cash_flow_agent")
    seq_workflow.add_edge("cash_flow_agent", "risk_agent")
    seq_workflow.add_edge("risk_agent", "communication_agent")
    seq_workflow.add_edge("communication_agent", "report_agent")
    seq_workflow.add_edge("report_agent", END)
    
    return seq_workflow.compile()
