import asyncio
import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "work_ticket.db")

    logger.info(f"Connecting to {db_path} to clean data...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = {
        "surveys": ["survey_medium", "language"],
        "time_periods": ["interview_end", "interview_end_month_ops"],
        "locations": [
            "geo_ops",
            "px_region",
            "px_sub_region",
            "sub_region_1",
            "country_name_ops",
        ],
        "products": [
            "brand_ops",
            "product_group_ops",
            "product_series",
            "machine_type_4_digital",
        ],
        "so_informations": [
            "program",
            "trans_servdelivery",
            "warranty",
            "sdf_code",
            "sdf_description",
            "comm_channel",
            "accounting_indicator_adjusted_ops",
            "service_provider_name_m",
            "primary_vendor_name_m",
        ],
        "work_tickets": ["responseid", "why_osat_en_mask"],
    }

    for table, columns in tables.items():
        for col in columns:
            logger.info(f"Trimming {table}.{col}...")
            cursor.execute(
                f"UPDATE {table} SET {col} = TRIM({col}) WHERE {col} IS NOT NULL"
            )

    conn.commit()
    conn.close()
    logger.info("Data cleanup complete. Whitespace stripped from all standard columns.")


if __name__ == "__main__":
    clean_data()
