import argparse
import sys
import logging
from datetime import date
from typing import Optional

from daily_data_generator import generate_initial_dataset, generate_daily_record
from analysis_engine import analyze_business_performance
from llm_analyst import generate_llm_analysis
from email_reporter import send_daily_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daily_pipeline.log", mode="a")
    ]
)

def run_daily_pipeline(
    target_date: Optional[str] = None,
    event_type: Optional[str] = None,
    data_file: str = "business_data.csv"
) -> bool:
    """
    Executes the full end-to-end NovaCart Daily Business Analyst workflow:
    1. Generate/Verify Today's Row
    2. Analyze Business Performance
    3. Generate LLM Business Interpretation
    4. Build & Send Email Report
    """
    logging.info("==================================================")
    logging.info("Starting DhawalKart Daily Business Analyst Pipeline")
    logging.info("==================================================")

    # Step 1: Data Generation
    target_date_str = target_date or date.today().strftime("%Y-%m-%d")
    logging.info(f"Step 1: Generating/Verifying daily record for '{target_date_str}' (Event: {event_type or 'None'})...")
    daily_row = generate_daily_record(target_date=target_date_str, output_file=data_file, event_type=event_type)
    logging.info(f"Daily Data Ready: Traffic={daily_row['traffic']}, Revenue=₹{daily_row['revenue']:,.2f}, Orders={daily_row['orders']}")

    # Step 2: Deterministic Business Analysis
    logging.info("Step 2: Performing deterministic analysis and anomaly detection...")
    findings = analyze_business_performance(csv_file=data_file, target_date=target_date_str)
    logging.info(f"Analysis Complete: {findings['total_anomalies_detected']} anomalies detected across {findings['total_metrics_analyzed']} metrics.")

    # Step 3: LLM Business Analyst Interpretation
    logging.info("Step 3: Sending structured findings to LLM Business Analyst...")
    llm_report = generate_llm_analysis(findings)
    logging.info("LLM Analyst summary generated successfully.")

    # Step 4: Email Report & Dispatch
    logging.info("Step 4: Rendering HTML email report and attempting dispatch...")
    email_sent = send_daily_email(findings, llm_report)

    logging.info("==================================================")
    logging.info("DhawalKart Daily Pipeline Completed Successfully!")
    logging.info("==================================================")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DhawalKart Daily AI Business Analyst Pipeline")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (defaults to today)")
    parser.add_argument("--event", type=str, help="Optional simulated event (e.g., 'marketing_campaign', 'website_problem', 'payment_failure', 'product_quality_problem')")
    parser.add_argument("--reset-data", action="store_true", help="Regenerate initial 30-day historical dataset")

    args = parser.parse_args()

    if args.reset_data:
        logging.info("Resetting 30-day historical dataset...")
        generate_initial_dataset(days=30, output_file="business_data.csv")

    run_daily_pipeline(target_date=args.date, event_type=args.event)
