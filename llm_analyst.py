import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert e-commerce business analyst writing a daily report for DhawalKart.
Your job is to analyze today's performance based strictly on factual calculations provided by Python.

Strict Guidelines:
1. Conversational & Human Tone: Write in clear, natural, human language — as if you are a friendly senior analyst talking directly to the business owner over a morning coffee. Avoid stiff robotic jargon.
2. Factual Accuracy: Use ONLY the numbers and percentage changes explicitly provided. NEVER invent numbers.
3. Metric Relationships: Explain HOW metrics connect naturally (e.g., "Revenue grew today driven mostly by higher order conversions rather than raw traffic").
4. Distinguish Facts from Hypotheses: State calculated changes as facts, and state interpretations gently (e.g., "Hypothesis: ...", "Possible reason: ...").

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
        prompt += (
            f"- {f['display_name']}: Today = {f['today_value']:,.2f} | Yesterday = {f['yesterday_value']:,.2f} "
            f"({f['pct_vs_yesterday']:+.2f}%) | 7d Avg = {f['avg_7d']:,.2f} ({f['pct_vs_7d']:+.2f}%) | "
            f"30d Avg = {f['avg_30d']:,.2f} ({f['pct_vs_30d']:+.2f}%) | Severity = {f['severity']}\n"
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
    Sends structured findings to the designated LLM provider (ollama, openai, gemini, or fallback).
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

    # 2. Try OpenAI if selected or key present
    openai_key = os.getenv("OPENAI_API_KEY")
    if provider == "openai" or (provider == "ollama" and openai_key):
        if openai_key:
            try:
                import openai
                print("[LLM] Querying OpenAI API (gpt-4o-mini)...")
                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[Warning] OpenAI API call failed: {e}")

    # 3. Fallback mock analyst report
    return generate_mock_analysis(findings_data)


def generate_mock_analysis(findings_data: Dict[str, Any]) -> str:
    """Generates a warm, natural human-like analyst report without 'Areas of Concern'."""
    date_str = findings_data.get("analysis_date", "Today")
    anomalies = findings_data.get("anomalies", [])
    findings = findings_data.get("findings", [])

    metric_map = {f['metric']: f for f in findings}
    rev = metric_map.get('revenue', {})
    trf = metric_map.get('traffic', {})
    ord_ = metric_map.get('orders', {})

    report = f"### Executive Summary\n"
    report += f"Good morning! Here is your daily performance summary for **DhawalKart** on **{date_str}**.\n\n"
    report += f"Revenue reached **₹{rev.get('today_value', 0):,.2f}** ({rev.get('pct_vs_yesterday', 0):+.1f}% vs yesterday), with total website traffic at **{trf.get('today_value', 0):,.0f} visitors** and **{ord_.get('today_value', 0):,.0f} completed orders**.\n"

    report += "\n### Key Performance Highlights & Metric Stories\n"
    report += f"Looking closely at today's numbers, revenue changed by **{rev.get('pct_vs_yesterday', 0):+.1f}%** compared to yesterday. "
    report += f"This movement closely mirrors our order volume ({ord_.get('pct_vs_yesterday', 0):+.1f}% change with {ord_.get('today_value', 0):,.0f} total orders completed). "
    report += f"Traffic was recorded at **{trf.get('today_value', 0):,.0f} visits** ({trf.get('pct_vs_yesterday', 0):+.1f}% vs yesterday), showing healthy stability across user acquisition.\n"

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
