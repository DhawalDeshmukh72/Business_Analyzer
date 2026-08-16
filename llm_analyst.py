import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

INTEGER_METRICS = {"traffic", "orders", "refunds", "new_customers"}

def fmt_val(metric: str, val: float) -> str:
    """Formats count metrics as integers and currency/rates with appropriate decimals."""
    if metric in INTEGER_METRICS:
        return f"{int(round(val)):,}"
    return f"{val:,.2f}"

SYSTEM_PROMPT = """You are an expert e-commerce business analyst writing a daily report for DhawalKart.
Your job is to analyze today's performance based strictly on factual calculations provided by Python.

Strict Guidelines:
1. Conversational & Human Tone: Write in clear, natural, human language — as if you are a friendly senior analyst talking directly to the business owner over a morning coffee. Avoid stiff robotic jargon.
2. Factual Accuracy: Use ONLY the numbers and percentage changes explicitly provided. NEVER invent numbers.
3. Metric Relationships: Explain HOW metrics connect naturally (e.g., "Revenue grew today driven mostly by higher order conversions rather than raw traffic").
4. Distinguish Facts from Hypotheses: State calculated changes as facts, and state interpretations gently (e.g., "Hypothesis: ...", "Possible reason: ...").
5. INTEGER METRICS: For count metrics (Website Traffic, Orders, Refunds, New Customers), state values as whole numbers (e.g., 5,553 visits, 143 orders, 4 refunds, 93 customers), never with decimal places (.00).

Structure your markdown response cleanly using these exact section headers:
### Executive Summary
### Key Performance Highlights & Metric Stories
### Analyst Recommendations & Next Steps
"""

def build_analyst_prompt(findings_data: Dict[str, Any]) -> str:
    """Builds a structured prompt containing deterministic findings for the LLM."""
    date_str = findings_data.get("analysis_date", "Today")
    findings = findings_data.get("findings", [])

    prompt = f"Daily Business Performance Data for DhawalKart ({date_str}):\n\n"
    prompt += "Overview:\n"
    prompt += f"- Total Metrics Analyzed: {findings_data.get('total_metrics_analyzed')}\n"
    prompt += f"- Total Anomalies Detected: {findings_data.get('total_anomalies_detected')}\n\n"

    prompt += "Detailed Metric Findings:\n"
    for f in findings:
        val_str = fmt_val(f['metric'], f['today_value'])
        yest_str = fmt_val(f['metric'], f['yesterday_value'])
        avg7_str = fmt_val(f['metric'], f['avg_7d'])
        avg30_str = fmt_val(f['metric'], f['avg_30d'])
        prompt += (
            f"- {f['display_name']}: Today = {val_str} | Yesterday = {yest_str} "
            f"({f['pct_vs_yesterday']:+.2f}%) | 7d Avg = {avg7_str} ({f['pct_vs_7d']:+.2f}%) | "
            f"30d Avg = {avg30_str} ({f['pct_vs_30d']:+.2f}%) | Severity = {f['severity']}\n"
        )

    prompt += "\nPlease write a warm, concise, human daily analysis report for the founder of DhawalKart."
    return prompt


def query_ollama(prompt: str, model: str = "llama3") -> Optional[str]:
    """Queries local Ollama server at http://localhost:11434."""
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("message", {}).get("content", "")
    except Exception as e:
        print(f"[Notice] Ollama request to '{url}' failed ({e}).")
        return None


def generate_llm_analysis(
    findings_data: Dict[str, Any],
    provider: Optional[str] = None
) -> str:
    """
    Sends structured findings to the designated LLM provider (ollama or fallback).
    """
    provider = provider or os.getenv("LLM_PROVIDER", "ollama").lower()
    prompt = build_analyst_prompt(findings_data)

    # 1. Try Ollama if selected or default
    if provider in ["ollama", "local"]:
        model = os.getenv("OLLAMA_MODEL", "llama3")
        print(f"[LLM] Querying local Ollama model '{model}' for DhawalKart analysis...")
        output = query_ollama(prompt, model=model)
        if output:
            return output
        print("[Notice] Falling back to natural analyst report because Ollama server is not running.")

    # 2. Fallback mock analyst report
    return generate_mock_analysis(findings_data)


def generate_mock_analysis(findings_data: Dict[str, Any]) -> str:
    """Generates a warm, natural human-like analyst report with clean integer formatting for count metrics."""
    date_str = findings_data.get("analysis_date", "Today")
    findings = findings_data.get("findings", [])

    metric_map = {f['metric']: f for f in findings}
    rev = metric_map.get('revenue', {})
    trf = metric_map.get('traffic', {})
    ord_ = metric_map.get('orders', {})

    report = f"### Executive Summary\n"
    report += f"Good morning! Here is your daily performance summary for **DhawalKart** on **{date_str}**.\n\n"
    report += f"Revenue reached **₹{rev.get('today_value', 0):,.2f}** ({rev.get('pct_vs_yesterday', 0):+.1f}% vs yesterday), with total website traffic at **{int(round(trf.get('today_value', 0))):,} visitors** and **{int(round(ord_.get('today_value', 0))):,} completed orders**.\n"

    report += "\n### Key Performance Highlights & Metric Stories\n"
    report += f"Looking closely at today's numbers, revenue changed by **{rev.get('pct_vs_yesterday', 0):+.1f}%** compared to yesterday. "
    report += f"This movement closely mirrors our order volume ({ord_.get('pct_vs_yesterday', 0):+.1f}% change with {int(round(ord_.get('today_value', 0))):,} total orders completed). "
    report += f"Traffic was recorded at **{int(round(trf.get('today_value', 0))):,} visits** ({trf.get('pct_vs_yesterday', 0):+.1f}% vs yesterday), showing healthy stability across user acquisition.\n"

    report += "\n### Analyst Recommendations & Next Steps\n"
    report += "1. **Maintain Momentum**: Current marketing spend and traffic ratios are well-aligned.\n"
    report += "2. **Inventory & Order Check**: Ensure stock levels remain healthy for top-performing items.\n"

    return report


if __name__ == "__main__":
    from analysis_engine import analyze_business_performance
    data = analyze_business_performance()
    summary = generate_llm_analysis(data)
    print("\n--- Generated Business Analyst Summary ---")
    print(summary)
