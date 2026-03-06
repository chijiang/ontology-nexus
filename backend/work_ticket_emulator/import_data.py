import os
import pandas as pd
import logging
import hashlib
from sqlalchemy.orm import Session
from .database import sync_engine, sync_session_maker
from .models import (
    Survey,
    Location,
    Product,
    SOInformation,
    WorkTicket,
    Base,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_str(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


def safe_int(val):
    if pd.isna(val) or val is None:
        return 0
    try:
        return int(val)
    except:
        return 0


def create_hash_key(*args):
    """Creates a unique hash key for a combination of strings to use as a deduplication dict key"""
    return hashlib.md5("|".join([str(a) for a in args]).encode("utf-8")).hexdigest()


def import_data(excel_path: str):
    logger.info("Initializing database schema...")
    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)

    logger.info(f"Loading Excel file: {excel_path} (This might take a minute)")
    df = pd.read_excel(excel_path, dtype={"responseid": str})
    df = df.where(pd.notnull(df), None)
    total_rows = len(df)
    logger.info(f"Loaded {total_rows} rows from Excel.")

    with sync_session_maker() as session:
        # Caches to avoid duplicate DB insertions during processing
        survey_cache = {}
        location_cache = {}
        product_cache = {}
        so_info_cache = {}

        batch_size = 10000
        tickets_batch = []

        seen_response_ids = set()

        for i, row in df.iterrows():
            if i > 0 and i % 50000 == 0:
                logger.info(f"Processed {i}/{total_rows} rows...")

            rid = safe_str(row.get("responseid"))
            if not rid or rid in seen_response_ids:
                continue
            seen_response_ids.add(rid)

            # --- Survey ---
            s_medium = safe_str(row.get("Survey_Medium"))
            s_lang = safe_str(row.get("language"))
            s_key = create_hash_key(s_medium, s_lang)
            if s_key not in survey_cache:
                survey = Survey(survey_medium=s_medium, language=s_lang)
                session.add(survey)
                session.flush()  # get id
                survey_cache[s_key] = survey.id
            survey_id = survey_cache[s_key]

            # --- Location ---
            l_geo = safe_str(row.get("geo_ops"))
            l_pxr = safe_str(row.get("PX_Region"))
            l_pxs = safe_str(row.get("PX_Sub_Region"))
            l_sr = safe_str(row.get("sub_region_1"))
            l_cnt = safe_str(row.get("country_name_ops"))
            l_key = create_hash_key(l_geo, l_pxr, l_pxs, l_sr, l_cnt)
            if l_key not in location_cache:
                loc = Location(
                    geo_ops=l_geo,
                    px_region=l_pxr,
                    px_sub_region=l_pxs,
                    sub_region_1=l_sr,
                    country_name_ops=l_cnt,
                )
                session.add(loc)
                session.flush()
                location_cache[l_key] = loc.id
            location_id = location_cache[l_key]

            # --- Product ---
            p_br = safe_str(row.get("brand_ops"))
            p_grp = safe_str(row.get("product_group_ops"))
            p_ser = safe_str(row.get("product_series"))
            p_mac = safe_str(row.get("machine_type_4_digital"))
            p_key = create_hash_key(p_br, p_grp, p_ser, p_mac)
            if p_key not in product_cache:
                prod = Product(
                    brand_ops=p_br,
                    product_group_ops=p_grp,
                    product_series=p_ser,
                    machine_type_4_digital=p_mac,
                )
                session.add(prod)
                session.flush()
                product_cache[p_key] = prod.id
            product_id = product_cache[p_key]

            # --- SOInformation ---
            so_prg = safe_str(row.get("program"))
            so_trs = safe_str(row.get("trans_servdelivery"))
            so_war = safe_str(row.get("Warranty"))
            so_sdf = safe_str(row.get("sdf_code"))
            so_sdd = safe_str(row.get("sdf_description"))
            so_com = safe_str(row.get("comm_channel"))
            so_acc = safe_str(row.get("accounting_indicator_adjusted_ops"))
            so_sp = safe_str(row.get("service_provider_name_m"))
            so_pv = safe_str(row.get("Primary_Vendor_name_m"))
            so_key = create_hash_key(
                so_prg, so_trs, so_war, so_sdf, so_sdd, so_com, so_acc, so_sp, so_pv
            )
            if so_key not in so_info_cache:
                so = SOInformation(
                    program=so_prg,
                    trans_servdelivery=so_trs,
                    warranty=so_war,
                    sdf_code=so_sdf,
                    sdf_description=so_sdd,
                    comm_channel=so_com,
                    accounting_indicator_adjusted_ops=so_acc,
                    service_provider_name_m=so_sp,
                    primary_vendor_name_m=so_pv,
                )
                session.add(so)
                session.flush()
                so_info_cache[so_key] = so.id
            so_information_id = so_info_cache[so_key]

            # --- WorkTicket ---
            ticket = WorkTicket(
                responseid=safe_str(row.get("responseid")),
                osat=safe_int(row.get("OSAT")),
                why_osat_en_mask=safe_str(row.get("WhyOSAT_en_mask")),
                first_time_resolution=safe_int(row.get("First_Time_Resolution")),
                ease_use=safe_int(row.get("Ease_Use")),
                survey_id=survey_id,
                interview_end=safe_str(row.get("interview_end")),
                interview_end_month_ops=safe_str(row.get("interview_end_month_ops")),
                location_id=location_id,
                product_id=product_id,
                so_information_id=so_information_id,
            )
            tickets_batch.append(ticket)

            if len(tickets_batch) >= batch_size:
                session.bulk_save_objects(tickets_batch)
                session.commit()
                tickets_batch = []

        if tickets_batch:
            session.bulk_save_objects(tickets_batch)
            session.commit()

        logger.info("Import complete.")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "t3b_sampledata_for POC.xlsx")
    import_data(data_path)
