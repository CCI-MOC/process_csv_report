import datetime
import json
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_institution_from_pi(institute_map, pi_uname):
    institution_key = pi_uname.split("@")[-1]
    institution_name = institute_map.get(institution_key, "")

    if institution_name == "":
        logger.warn(f"PI name {pi_uname} does not match any institution!")

    return institution_name


def load_institute_map() -> dict:
    with open("process_report/institute_map.json", "r") as f:
        institute_map = json.load(f)

    return institute_map


def get_iso8601_time():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")


def compare_invoice_month(month_1, month_2):
    """Returns True if 1st date is later than 2nd date"""
    dt1 = datetime.datetime.strptime(month_1, "%Y-%m")
    dt2 = datetime.datetime.strptime(month_2, "%Y-%m")
    return dt1 > dt2
