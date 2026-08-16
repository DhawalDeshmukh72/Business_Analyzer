import pandas as pd
import numpy as np
import os
from datetime import date, timedelta

EVENTS = {
    "marketing_campaign": {
        "traffic_mult": (1.25, 1.45),
        "conv_mult": (1.1, 1.25),
        "aov_mult": (1.0, 1.05),
        "refund_mult": (1.0, 1.2),
    },
    "website_problem": {
        "traffic_mult": (0.50, 0.70),
        "conv_mult": (0.6, 0.8),
        "aov_mult": (0.9, 1.0),
        "refund_mult": (1.0, 1.5),
    },
    "payment_failure": {
        "traffic_mult": (0.95, 1.05),
        "conv_mult": (0.3, 0.5),
        "aov_mult": (1.0, 1.0),
        "refund_mult": (1.0, 1.2),
    },
    "product_quality_problem": {
        "traffic_mult": (0.95, 1.05),
        "conv_mult": (0.95, 1.05),
        "aov_mult": (1.0, 1.0),
        "refund_mult": (3.5, 6.0),
    },
    "successful_promotion": {
        "traffic_mult": (1.20, 1.35),
        "conv_mult": (1.20, 1.40),
        "aov_mult": (1.0, 1.1),
        "refund_mult": (1.0, 1.2),
    }
}

def generate_initial_dataset(days=30, output_file="business_data.csv", seed=42):
    """
    Generates an initial historical dataset for DhawalKart with realistic daily variation
    and internal metric consistency.
    """
    if seed is not None:
        np.random.seed(seed)

    start_date = date.today() - timedelta(days=days - 1)
    data = []

    # Starting business assumptions
    traffic = 5000
    conversion_rate = 3.0
    average_order_value = 500.0

    for i in range(days):
        current_date = start_date + timedelta(days=i)

        # Normal daily variation in traffic
        traffic_change = np.random.normal(0, 0.04)
        traffic = int(max(1000, traffic * (1 + traffic_change)))

        # Conversion rate variation (bounded between 1.5% and 5.0%)
        conversion_rate += np.random.normal(0, 0.08)
        conversion_rate = max(1.5, min(conversion_rate, 5.0))

        # Orders derived from traffic and conversion rate
        orders = int(traffic * (conversion_rate / 100.0))

        # Average Order Value variation
        average_order_value += np.random.normal(0, 5)
        average_order_value = max(300.0, average_order_value)

        # Revenue derived from orders and AOV
        revenue = round(orders * average_order_value, 2)

        # Marketing spend related to traffic volume
        marketing_spend = round(traffic * np.random.uniform(2.5, 3.5), 2)

        # Operating cost related to revenue
        operating_cost = round(revenue * np.random.uniform(0.15, 0.25), 2)

        # Refunds related to order volume (1% to 4%)
        refunds = max(0, int(orders * np.random.uniform(0.01, 0.04)))

        # New customers related to order volume (55% to 75%)
        new_customers = max(0, int(orders * np.random.uniform(0.55, 0.75)))

        data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "traffic": traffic,
            "orders": orders,
            "conversion_rate": round(conversion_rate, 2),
            "revenue": revenue,
            "marketing_spend": marketing_spend,
            "operating_cost": operating_cost,
            "refunds": refunds,
            "new_customers": new_customers
        })

    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    
    # Also sync to SQLite database
    try:
        from database import save_df_to_db
        save_df_to_db(df, replace=True)
        print("Synchronized historical dataset with SQLite database 'business_data.db'.")
    except Exception as e:
        print(f"[Notice] SQLite sync skipped: {e}")

    print(f"Successfully generated {days} days of historical business data in '{output_file}'.")
    return df


def generate_daily_record(target_date=None, output_file="business_data.csv", event_type=None):
    """
    Appends exactly one new row for `target_date` (defaults to today).
    Avoids duplicate entries for the same date.
    Optionally simulates business events (e.g., 'marketing_campaign', 'website_problem', etc.).
    """
    if not os.path.exists(output_file):
        print(f"File '{output_file}' not found. Generating initial dataset first...")
        df = generate_initial_dataset(days=30, output_file=output_file)
    else:
        df = pd.read_csv(output_file)

    if target_date is None:
        target_date_str = date.today().strftime("%Y-%m-%d")
    elif isinstance(target_date, date):
        target_date_str = target_date.strftime("%Y-%m-%d")
    else:
        target_date_str = str(target_date)

    # Check for duplicate in CSV and SQLite
    if target_date_str in df['date'].astype(str).values:
        print(f"Record for date '{target_date_str}' already exists in '{output_file}'. Skipping duplicate insertion.")
        return df[df['date'].astype(str) == target_date_str].iloc[-1].to_dict()

    # Get baseline from previous day / recent trend
    last_row = df.iloc[-1]
    prev_traffic = float(last_row['traffic'])
    prev_conv = float(last_row['conversion_rate'])
    prev_orders = float(last_row['orders'])
    prev_revenue = float(last_row['revenue'])
    prev_aov = (prev_revenue / prev_orders) if prev_orders > 0 else 500.0

    # Base variations
    traffic_change = np.random.normal(0, 0.04)
    traffic = int(max(1000, prev_traffic * (1 + traffic_change)))

    conv_rate = prev_conv + np.random.normal(0, 0.08)
    conv_rate = max(1.5, min(conv_rate, 5.0))

    aov = prev_aov + np.random.normal(0, 5)
    aov = max(300.0, aov)

    refund_pct = np.random.uniform(0.01, 0.04)

    # Apply event modifications if event_type specified
    if event_type and event_type in EVENTS:
        event = EVENTS[event_type]
        print(f"Simulating business event: '{event_type}'")
        t_mult = np.random.uniform(*event['traffic_mult'])
        c_mult = np.random.uniform(*event['conv_mult'])
        a_mult = np.random.uniform(*event['aov_mult'])
        r_mult = np.random.uniform(*event['refund_mult'])

        traffic = int(traffic * t_mult)
        conv_rate = max(0.5, min(conv_rate * c_mult, 8.0))
        aov = max(200.0, aov * a_mult)
        refund_pct = min(0.30, refund_pct * r_mult)

    # Calculate metrics
    orders = int(traffic * (conv_rate / 100.0))
    revenue = round(orders * aov, 2)
    marketing_spend = round(traffic * np.random.uniform(2.5, 3.5), 2)
    operating_cost = round(revenue * np.random.uniform(0.15, 0.25), 2)
    refunds = max(0, int(orders * refund_pct))
    new_customers = max(0, int(orders * np.random.uniform(0.55, 0.75)))

    new_record = {
        "date": target_date_str,
        "traffic": traffic,
        "orders": orders,
        "conversion_rate": round(conv_rate, 2),
        "revenue": revenue,
        "marketing_spend": marketing_spend,
        "operating_cost": operating_cost,
        "refunds": refunds,
        "new_customers": new_customers
    }

    # Append to existing DataFrame and save to CSV & SQLite
    df_updated = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    df_updated.to_csv(output_file, index=False)

    try:
        from database import insert_record_to_db
        insert_record_to_db(new_record)
    except Exception as e:
        print(f"[Notice] SQLite record insert skipped: {e}")

    print(f"Successfully added new daily record for '{target_date_str}' to '{output_file}' and SQLite database.")
    return new_record



if __name__ == "__main__":
    df = generate_initial_dataset()
    print("\nDataset Preview (First & Last 3 rows):")
    print(pd.concat([df.head(3), df.tail(3)]))