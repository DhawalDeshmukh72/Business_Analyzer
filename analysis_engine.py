import pandas as pd
import numpy as np
import os
from typing import Dict, List, Any, Optional

DEFAULT_THRESHOLDS = {
    "noteworthy": 10.0,
    "significant": 20.0,
    "major": 30.0
}

METRIC_DISPLAY_NAMES = {
    "traffic": "Website Traffic",
    "orders": "Orders",
    "conversion_rate": "Conversion Rate (%)",
    "revenue": "Revenue",
    "marketing_spend": "Marketing Spend",
    "operating_cost": "Operating Cost",
    "refunds": "Refunds",
    "new_customers": "New Customers"
}

def calculate_percentage_change(current: float, baseline: float) -> Optional[float]:
    """Calculates percentage change safely handling zero division."""
    if baseline == 0 or pd.isna(baseline) or pd.isna(current):
        return 0.0 if current == 0 else None
    return round(((current - baseline) / baseline) * 100.0, 2)


def determine_severity(pct_changes: List[Optional[float]], thresholds: Dict[str, float]) -> str:
    """Determines change severity based on maximum percentage change against baselines."""
    valid_changes = [abs(c) for c in pct_changes if c is not None]
    if not valid_changes:
        return "Normal"
    
    max_change = max(valid_changes)
    if max_change >= thresholds.get("major", 30.0):
        return "Major"
    elif max_change >= thresholds.get("significant", 20.0):
        return "Significant"
    elif max_change >= thresholds.get("noteworthy", 10.0):
        return "Noteworthy"
    return "Normal"


def determine_direction(pct_change: Optional[float]) -> str:
    """Determines directional change."""
    if pct_change is None or abs(pct_change) < 0.1:
        return "Unchanged"
    return "Increase" if pct_change > 0 else "Decrease"


def analyze_business_performance(
    csv_file: str = "business_data.csv",
    target_date: Optional[str] = None,
    thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Deterministic analysis engine that calculates daily, 7-day average, and 30-day average
    percentage changes across all metrics, assigns severity levels, and structures findings.
    """
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Data file '{csv_file}' not found.")

    df = pd.read_csv(csv_file)
    if df.empty:
        raise ValueError(f"Data file '{csv_file}' is empty.")

    # Ensure dates are sorted
    df['date'] = df['date'].astype(str)
    df = df.sort_values('date').reset_index(drop=True)

    # Determine target date index
    if target_date is None:
        target_idx = len(df) - 1
    else:
        match = df.index[df['date'] == str(target_date)].tolist()
        if not match:
            raise ValueError(f"Date '{target_date}' not found in dataset.")
        target_idx = match[0]

    current_row = df.iloc[target_idx]
    analysis_date = current_row['date']

    if target_idx < 1:
        raise ValueError("At least 2 days of historical data are required to perform daily analysis.")

    yesterday_row = df.iloc[target_idx - 1]

    # Preceding historical windows (excluding current day for baselines)
    history_7d = df.iloc[max(0, target_idx - 7):target_idx]
    history_30d = df.iloc[max(0, target_idx - 30):target_idx]

    active_thresholds = DEFAULT_THRESHOLDS.copy()
    if thresholds:
        active_thresholds.update(thresholds)

    metrics = list(METRIC_DISPLAY_NAMES.keys())
    findings = []
    anomalies = []

    for metric in metrics:
        today_val = float(current_row[metric])
        yesterday_val = float(yesterday_row[metric])
        avg_7d = float(history_7d[metric].mean())
        avg_30d = float(history_30d[metric].mean())

        pct_vs_yesterday = calculate_percentage_change(today_val, yesterday_val)
        pct_vs_7d = calculate_percentage_change(today_val, avg_7d)
        pct_vs_30d = calculate_percentage_change(today_val, avg_30d)

        severity = determine_severity([pct_vs_yesterday, pct_vs_7d, pct_vs_30d], active_thresholds)
        direction = determine_direction(pct_vs_yesterday)

        context_info = (
            f"Yesterday: {yesterday_val:,.2f} ({pct_vs_yesterday:+.1f}%); "
            f"7-Day Avg: {avg_7d:,.2f} ({pct_vs_7d:+.1f}%); "
            f"30-Day Avg: {avg_30d:,.2f} ({pct_vs_30d:+.1f}%)"
        )

        finding = {
            "metric": metric,
            "display_name": METRIC_DISPLAY_NAMES[metric],
            "today_value": today_val,
            "yesterday_value": yesterday_val,
            "pct_vs_yesterday": pct_vs_yesterday,
            "avg_7d": round(avg_7d, 2),
            "pct_vs_7d": pct_vs_7d,
            "avg_30d": round(avg_30d, 2),
            "pct_vs_30d": pct_vs_30d,
            "direction": direction,
            "severity": severity,
            "context": context_info
        }

        findings.append(finding)
        if severity in ["Noteworthy", "Significant", "Major"]:
            anomalies.append(finding)

    # Calculate high-level summary KPIs
    summary = {
        "analysis_date": analysis_date,
        "total_metrics_analyzed": len(metrics),
        "total_anomalies_detected": len(anomalies),
        "thresholds_used": active_thresholds,
        "findings": findings,
        "anomalies": anomalies
    }

    return summary


if __name__ == "__main__":
    import json
    report = analyze_business_performance()
    print(f"--- Analysis Report for {report['analysis_date']} ---")
    print(f"Anomalies Detected: {report['total_anomalies_detected']}")
    for f in report['findings']:
        print(f"\nMetric: {f['display_name']}")
        print(f"  Today: {f['today_value']:,.2f}")
        print(f"  vs Yesterday: {f['pct_vs_yesterday']:+.2f}% | Direction: {f['direction']}")
        print(f"  vs 7-Day Avg: {f['pct_vs_7d']:+.2f}% | vs 30-Day Avg: {f['pct_vs_30d']:+.2f}%")
        print(f"  Severity: {f['severity']}")
