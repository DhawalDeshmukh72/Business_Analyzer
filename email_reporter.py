import os
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

INTEGER_METRICS = {"traffic", "orders", "refunds", "new_customers"}

def format_date_str(date_str: str) -> str:
    """Formats YYYY-MM-DD to '16 Aug 2026' style."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d %b %Y")
    except Exception:
        return date_str


def format_metric_value(metric_name: str, value: float) -> str:
    """Formats count metrics as integers and currency/rates with appropriate decimals."""
    if metric_name in INTEGER_METRICS:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}"


def convert_markdown_to_clean_html(markdown_text: str) -> str:
    """
    Converts markdown text to clean HTML with strict, uniform font styling (14px base),
    rendering main bullets and sub-bullets in structured, visually appealing hierarchy.
    """
    lines = markdown_text.strip().split("\n")
    html_lines = []

    for line in lines:
        raw_line = line.rstrip()
        if not raw_line.strip():
            continue

        # Handle Headings (convert to clean, uniform 15px bold section titles)
        if raw_line.strip().startswith("### ") or raw_line.strip().startswith("## ") or raw_line.strip().startswith("# "):
            heading_text = re.sub(r"^#+\s*", "", raw_line.strip())
            html_lines.append(
                f'<div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 24px; margin-bottom: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">'
                f'{heading_text}</div>'
            )

        # Handle Sub-bullets (indented lines starting with '  -' or '    -')
        elif raw_line.startswith("  - ") or raw_line.startswith("    - ") or raw_line.startswith("\t- "):
            content = raw_line.strip()[2:].strip()
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong style='color: #1e293b;'>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append(
                f'<div style="font-size: 13px; line-height: 1.5; color: #475569; margin-left: 24px; margin-bottom: 4px; padding-left: 8px; border-left: 2px solid #cbd5e1;">'
                f'&bull; {content}</div>'
            )

        # Handle Main Bullet points
        elif raw_line.strip().startswith("- ") or raw_line.strip().startswith("* "):
            content = raw_line.strip()[2:].strip()
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong style='color: #0f172a;'>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append(
                f'<div style="font-size: 14px; font-weight: 600; line-height: 1.6; color: #0f172a; margin-top: 10px; margin-bottom: 4px;">'
                f'&bull; {content}</div>'
            )

        # Handle Numbered lists
        elif re.match(r"^\d+\.\s", raw_line.strip()):
            content = re.sub(r"^\d+\.\s", "", raw_line.strip())
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong style='color: #0f172a;'>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append(
                f'<div style="font-size: 14px; line-height: 1.6; color: #334155; margin-left: 12px; margin-bottom: 6px;">'
                f'{raw_line.strip().split(".")[0]}. {content}</div>'
            )

        # Regular Paragraphs
        else:
            content = raw_line.strip()
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong style='color: #0f172a;'>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            html_lines.append(
                f'<p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 8px 0;">{content}</p>'
            )

    return "".join(html_lines)


def build_plain_text_email(findings_data: Dict[str, Any], llm_markdown_report: str) -> str:
    """Renders clean plain-text alternative for anti-spam filters."""
    date_formatted = format_date_str(findings_data.get("analysis_date", ""))
    text = f"DhawalKart Daily Business Report — {date_formatted}\n\n"
    text += f"Daily Overview:\n"
    text += f"- Total Metrics Tracked: {findings_data.get('total_metrics_analyzed')}\n"
    text += f"- Anomalies Flagged: {findings_data.get('total_anomalies_detected')}\n\n"
    text += "--------------------------------------------------\n"
    text += llm_markdown_report
    text += "\n--------------------------------------------------\n"
    text += f"Generated automatically by DhawalKart AI Business Analyst."
    return text


def build_html_email(findings_data: Dict[str, Any], llm_markdown_report: str) -> str:
    """Renders a responsive, professional HTML daily report email for DhawalKart."""
    date_formatted = format_date_str(findings_data.get("analysis_date", ""))
    findings = findings_data.get("findings", [])

    body_html = convert_markdown_to_clean_html(llm_markdown_report)

    table_rows = ""
    for f in findings:
        sev_color = "#3b82f6"
        if f['severity'] == "Major":
            sev_color = "#ef4444"
        elif f['severity'] == "Significant":
            sev_color = "#f97316"
        elif f['severity'] == "Noteworthy":
            sev_color = "#eab308"

        pct = f['pct_vs_yesterday']
        pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
        pct_color = "#16a34a" if (pct or 0) > 0 else ("#dc2626" if (pct or 0) < 0 else "#64748b")
        formatted_val = format_metric_value(f['metric'], f['today_value'])

        table_rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 9px 12px; font-weight: 600; color: #1e293b; font-size: 13px;">{f['display_name']}</td>
            <td style="padding: 9px 12px; color: #334155; font-size: 13px;">{formatted_val}</td>
            <td style="padding: 9px 12px; color: {pct_color}; font-weight: 600; font-size: 13px;">{pct_str}</td>
            <td style="padding: 9px 12px; color: #64748b; font-size: 13px;">{f['pct_vs_7d']:+.1f}%</td>
            <td style="padding: 9px 12px;">
                <span style="background-color: {sev_color}18; color: {sev_color}; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; display: inline-block;">
                    {f['severity']}
                </span>
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #334155; margin: 0; padding: 0; font-size: 14px; line-height: 1.6; }}
            .container {{ max-width: 650px; margin: 20px auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 24px 28px; text-align: left; }}
            .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }}
            .header p {{ margin: 4px 0 0 0; color: #94a3b8; font-size: 13px; }}
            .content {{ padding: 28px; font-size: 14px; line-height: 1.6; color: #334155; }}
            .summary-card {{ background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 16px; border-radius: 0 6px 6px 0; margin-bottom: 20px; font-size: 14px; line-height: 1.5; }}
            .metrics-table {{ width: 100%; border-collapse: collapse; margin: 16px 0 24px 0; font-size: 13px; text-align: left; }}
            .metrics-table th {{ background-color: #f1f5f9; padding: 9px 12px; color: #475569; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; }}
            .footer {{ background-color: #f8fafc; padding: 18px 28px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>DhawalKart Daily Business Report</h1>
                <p>{date_formatted} &bull; Executive Analyst Digest</p>
            </div>
            <div class="content">
                <div class="summary-card">
                    <strong style="color: #0f172a; font-size: 14px;">Daily Snapshot ({date_formatted}):</strong><br>
                    <span>Total Metrics Tracked: <strong style="color: #0f172a;">{findings_data.get('total_metrics_analyzed')}</strong> &bull; Anomalies Flagged: <strong style="color: #ef4444;">{findings_data.get('total_anomalies_detected')}</strong></span>
                </div>

                <div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 20px; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;">
                    Key Performance Metrics
                </div>
                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Today</th>
                            <th>vs Yesterday</th>
                            <th>vs 7-Day Avg</th>
                            <th>Severity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>

                <div style="font-size: 14px; line-height: 1.6; color: #334155;">
                    {body_html}
                </div>
            </div>
            <div class="footer">
                DhawalKart Automated AI Business Analyst System &bull; Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_daily_email(
    findings_data: Dict[str, Any],
    llm_markdown_report: str,
    output_preview_file: str = "email_preview.html"
) -> bool:
    """
    Generates and dispatches the daily business report email with proper MIME headers.
    """
    date_formatted = format_date_str(findings_data.get("analysis_date", ""))
    subject = f"DhawalKart Daily Business Report — {date_formatted}"
    html_content = build_html_email(findings_data, llm_markdown_report)
    plain_text = build_plain_text_email(findings_data, llm_markdown_report)

    with open(output_preview_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Email Reporter] Report preview saved locally to '{output_preview_file}'.")

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not sender_email or not sender_password or not recipient_email:
        print("[Notice] SMTP credentials not fully set in .env. Skipping live email dispatch.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"DhawalKart Analyst <{sender_email}>"
        msg["To"] = recipient_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")

        clean_password = sender_password.replace(" ", "")

        part_text = MIMEText(plain_text, "plain", "utf-8")
        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_text)
        msg.attach(part_html)

        print(f"[Email Reporter] Connecting to SMTP server '{smtp_server}:{smtp_port}'...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, clean_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())

        print(f"Successfully sent DhawalKart daily report email to '{recipient_email}'.")
        return True

    except Exception as e:
        print(f"[Error] Failed to send email via SMTP ({e}). Local preview file saved at '{output_preview_file}'.")
        return False


if __name__ == "__main__":
    from analysis_engine import analyze_business_performance
    from llm_analyst import generate_llm_analysis

    data = analyze_business_performance()
    summary = generate_llm_analysis(data)
    send_daily_email(data, summary)
