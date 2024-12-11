import os
import datetime
import yaml
import logging
import functools

import boto3


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@functools.lru_cache
def get_invoice_bucket():
    try:
        s3_resource = boto3.resource(
            service_name="s3",
            endpoint_url=os.environ.get(
                "S3_ENDPOINT", "https://s3.us-east-005.backblazeb2.com"
            ),
            aws_access_key_id=os.environ["S3_KEY_ID"],
            aws_secret_access_key=os.environ["S3_APP_KEY"],
        )
    except KeyError:
        logger.error(
            "Error: Please set the environment variables S3_KEY_ID and S3_APP_KEY"
        )
    return s3_resource.Bucket(os.environ.get("S3_BUCKET_NAME", "nerc-invoicing"))


def load_institute_list():
    with open("process_report/institute_list.yaml", "r") as f:
        institute_list = yaml.safe_load(f)

    return institute_list


def get_iso8601_time():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")


def compare_invoice_month(month_1, month_2):
    """Returns True if 1st date is later than 2nd date"""
    dt1 = datetime.datetime.strptime(month_1, "%Y-%m")
    dt2 = datetime.datetime.strptime(month_2, "%Y-%m")
    return dt1 > dt2


def get_month_diff(month_1, month_2):
    """Returns a positive integer if month_1 is ahead in time of month_2"""
    dt1 = datetime.datetime.strptime(month_1, "%Y-%m")
    dt2 = datetime.datetime.strptime(month_2, "%Y-%m")
    return (dt1.year - dt2.year) * 12 + (dt1.month - dt2.month)


def process_and_export_invoices(invoice_list, upload_to_s3):
    for invoice in invoice_list:
        invoice.process()
        invoice.export()
        if upload_to_s3:
            bucket = get_invoice_bucket()
            invoice.export_s3(bucket)
