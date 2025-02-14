import argparse
import sys
import datetime
import logging

import pandas
import pyarrow

from process_report import util
from process_report.invoices import (
    lenovo_invoice,
    nonbillable_invoice,
    billable_invoice,
    NERC_total_invoice,
    bu_internal_invoice,
    pi_specific_invoice,
    MOCA_prepaid_invoice,
)
from process_report.processors import (
    validate_pi_alias_processor,
    add_institution_processor,
    lenovo_processor,
    validate_billable_pi_processor,
    new_pi_credit_processor,
    bu_subsidy_processor,
    prepayment_processor,
)

### PI file field names
PI_PI_FIELD = "PI"
PI_FIRST_MONTH = "First Invoice Month"
PI_INITIAL_CREDITS = "Initial Credits"
PI_1ST_USED = "1st Month Used"
PI_2ND_USED = "2nd Month Used"
###


### Invoice field names
INVOICE_DATE_FIELD = "Invoice Month"
PROJECT_FIELD = "Project - Allocation"
PROJECT_ID_FIELD = "Project - Allocation ID"
PI_FIELD = "Manager (PI)"
INVOICE_EMAIL_FIELD = "Invoice Email"
INVOICE_ADDRESS_FIELD = "Invoice Address"
INSTITUTION_FIELD = "Institution"
INSTITUTION_ID_FIELD = "Institution - Specific Code"
SU_HOURS_FIELD = "SU Hours (GBhr or SUhr)"
SU_TYPE_FIELD = "SU Type"
RATE_FIELD = "Rate"
COST_FIELD = "Cost"
CREDIT_FIELD = "Credit"
CREDIT_CODE_FIELD = "Credit Code"
SUBSIDY_FIELD = "Subsidy"
BALANCE_FIELD = "Balance"
###

PI_S3_FILEPATH = "PIs/PI.csv"
ALIAS_S3_FILEPATH = "PIs/alias.csv"
PREPAY_DEBITS_S3_FILEPATH = "Prepay/prepay_debits.csv"


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_alias(alias_file):
    alias_dict = dict()

    try:
        with open(alias_file) as f:
            for line in f:
                pi_alias_info = line.strip().split(",")
                alias_dict[pi_alias_info[0]] = pi_alias_info[1:]
    except FileNotFoundError:
        logging.error("Validating PI aliases failed. Alias file does not exist")
        sys.exit(1)

    return alias_dict


def load_prepay_csv(prepay_credits_path, prepay_projects_path, prepay_contacts_path):
    return (
        pandas.read_csv(prepay_credits_path),
        pandas.read_csv(prepay_projects_path),
        pandas.read_csv(prepay_contacts_path),
    )


def get_iso8601_time():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")


def main():
    """Remove non-billable PIs and projects"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "csv_files",
        nargs="*",
        help="One or more CSV files that need to be processed",
    )
    parser.add_argument(
        "--fetch-from-s3",
        action="store_true",
        help="If set, fetches invoices from S3 storage. Requires environment variables for S3 authentication to be set",
    )
    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        help="If set, uploads all processed invoices and old PI file to S3",
    )
    parser.add_argument(
        "--invoice-month",
        required=True,
        help="Invoice month to process",
    )
    parser.add_argument(
        "--pi-file",
        required=True,
        help="File containing list of PIs that are non-billable",
    )
    parser.add_argument(
        "--projects-file",
        required=True,
        help="File containing list of projects that are non-billable",
    )
    parser.add_argument(
        "--timed-projects-file",
        required=True,
        help="File containing list of projects that are non-billable within a specified duration",
    )
    parser.add_argument(
        "--prepay-credits",
        required=False,
        default="prepaid_credits.csv",
        help="CSV listing all prepay group credits. Defaults to 'prepaid_credits.csv'",
    )
    parser.add_argument(
        "--prepay-projects",
        required=False,
        default="prepaid_projects.csv",
        help="CSV listing all prepay group projects. Defaults to 'prepaid_projects.csv'",
    )
    parser.add_argument(
        "--prepay-contacts",
        required=False,
        default="prepaid_contacts.csv",
        help="CSV listing all prepay group contact information. Defaults to 'prepaid_contacts.csv'",
    )

    parser.add_argument(
        "--nonbillable-file",
        required=False,
        default="nonbillable",
        help="Name of nonbillable file",
    )
    parser.add_argument(
        "--output-file",
        required=False,
        default="billable",
        help="Name of output file",
    )
    parser.add_argument(
        "--output-folder",
        required=False,
        default="pi_invoices",
        help="Name of output folder containing pi-specific invoice csvs",
    )
    parser.add_argument(
        "--BU-invoice-file",
        required=False,
        default="BU_Internal",
        help="Name of output csv for BU invoices",
    )
    parser.add_argument(
        "--NERC-total-invoice-file",
        required=False,
        default="NERC",
        help="Name of output csv for HU and BU invoice",
    )
    parser.add_argument(
        "--Lenovo-file",
        required=False,
        default="Lenovo",
        help="Name of output csv for Lenovo SU Types invoice",
    )
    parser.add_argument(
        "--old-pi-file",
        required=False,
        help="Name of csv file listing previously billed PIs. If not provided, defaults to fetching from S3",
    )
    parser.add_argument(
        "--alias-file",
        required=False,
        help="Name of alias file listing PIs with aliases (and their aliases). If not provided, defaults to fetching from S3",
    )
    parser.add_argument(
        "--prepay-debits",
        required=False,
        help="Name of csv file listing all prepay group debits. If not provided, defaults to fetching from S3",
    )
    parser.add_argument(
        "--new-pi-credit-amount",
        required=False,
        type=int,
        help="Amount of credit given to new PIs. If not provided, defaults to fetching from nerc-rates",
    )
    parser.add_argument(
        "--BU-subsidy-amount",
        required=False,
        type=int,
        help="Amount of subsidy given to BU PIs. If not provided, defaults to fetching from nerc-rates",
    )
    args = parser.parse_args()

    invoice_month = args.invoice_month

    csv_files = args.csv_files or fetch_s3_invoices(invoice_month)
    old_pi_file = args.old_pi_file or util.fetch_s3(PI_S3_FILEPATH)
    alias_file = args.alias_file or util.fetch_s3(ALIAS_S3_FILEPATH)
    alias_dict = load_alias(alias_file)
    prepay_debits_filepath = args.prepay_debits or util.fetch_s3(
        PREPAY_DEBITS_S3_FILEPATH
    )
    new_pi_credit_amount = args.new_pi_credit_amount or int(
        util.fetch_nerc_rates("New PI Credit", invoice_month)
    )
    bu_subsidy_amount = args.BU_subsidy_amount or int(
        util.fetch_nerc_rates("BU Subsidy", invoice_month)
    )
    prepay_credits, prepay_projects, prepay_info = load_prepay_csv(
        args.prepay_credits, args.prepay_projects, args.prepay_contacts
    )

    merged_dataframe = merge_csv(csv_files)

    pi = []
    projects = []
    with open(args.pi_file) as file:
        pi = [line.rstrip() for line in file]
    with open(args.projects_file) as file:
        projects = [line.rstrip() for line in file]

    logger.info("Invoice date: " + str(invoice_month))

    timed_projects_list = timed_projects(args.timed_projects_file, invoice_month)
    logger.info("The following timed-projects will not be billed for this period: ")
    logger.info(timed_projects_list)

    projects = list(set(projects + timed_projects_list))

    ### Preliminary processing

    validate_pi_alias_proc = validate_pi_alias_processor.ValidatePIAliasProcessor(
        "", invoice_month, merged_dataframe, alias_dict
    )
    validate_pi_alias_proc.process()

    add_institute_proc = add_institution_processor.AddInstitutionProcessor(
        "", invoice_month, validate_pi_alias_proc.data
    )
    add_institute_proc.process()

    lenovo_proc = lenovo_processor.LenovoProcessor(
        "", invoice_month, add_institute_proc.data
    )
    lenovo_proc.process()

    validate_billable_pi_proc = (
        validate_billable_pi_processor.ValidateBillablePIsProcessor(
            "", invoice_month, lenovo_proc.data, pi, projects
        )
    )
    validate_billable_pi_proc.process()

    new_pi_credit_proc = new_pi_credit_processor.NewPICreditProcessor(
        "",
        invoice_month,
        data=validate_billable_pi_proc.data,
        old_pi_filepath=old_pi_file,
        initial_credit_amount=new_pi_credit_amount,
        limit_new_pi_credit_to_partners=(
            util.fetch_nerc_rates(
                "Limit New PI Credit to MGHPCC Partners", invoice_month
            )
            == "True",
        ),
    )
    new_pi_credit_proc.process()

    bu_subsidy_proc = bu_subsidy_processor.BUSubsidyProcessor(
        "", invoice_month, new_pi_credit_proc.data.copy(), bu_subsidy_amount
    )
    bu_subsidy_proc.process()

    prepayment_proc = prepayment_processor.PrepaymentProcessor(
        "",
        invoice_month,
        bu_subsidy_proc.data,
        prepay_credits,
        prepay_projects,
        prepay_info,
        prepay_debits_filepath,
        args.upload_to_s3,
    )
    prepayment_proc.process()

    processed_data = prepayment_proc.data

    ### Initialize invoices

    lenovo_inv = lenovo_invoice.LenovoInvoice(
        name=args.Lenovo_file,
        invoice_month=invoice_month,
        data=processed_data,
    )
    nonbillable_inv = nonbillable_invoice.NonbillableInvoice(
        name=args.nonbillable_file,
        invoice_month=invoice_month,
        data=processed_data,
        nonbillable_pis=pi,
        nonbillable_projects=projects,
    )

    if args.upload_to_s3:
        backup_to_s3_old_pi_file(old_pi_file)

    billable_inv = billable_invoice.BillableInvoice(
        name=args.output_file,
        invoice_month=invoice_month,
        data=processed_data,
        old_pi_filepath=old_pi_file,
        updated_old_pi_df=new_pi_credit_proc.updated_old_pi_df,
    )

    nerc_total_inv = NERC_total_invoice.NERCTotalInvoice(
        name=args.NERC_total_invoice_file,
        invoice_month=invoice_month,
        data=processed_data,
    )

    bu_internal_inv = bu_internal_invoice.BUInternalInvoice(
        name=args.BU_invoice_file,
        invoice_month=invoice_month,
        data=processed_data,
    )

    pi_inv = pi_specific_invoice.PIInvoice(
        name=args.output_folder, invoice_month=invoice_month, data=processed_data
    )

    moca_prepaid_inv = MOCA_prepaid_invoice.MOCAPrepaidInvoice(
        name="", invoice_month=invoice_month, data=processed_data.copy()
    )

    util.process_and_export_invoices(
        [
            lenovo_inv,
            nonbillable_inv,
            billable_inv,
            nerc_total_inv,
            bu_internal_inv,
            pi_inv,
            moca_prepaid_inv,
        ],
        args.upload_to_s3,
    )


def fetch_s3_invoices(invoice_month):
    """Fetches usage invoices from S3 given invoice month"""
    s3_invoice_list = list()
    invoice_bucket = util.get_invoice_bucket()
    for obj in invoice_bucket.objects.filter(
        Prefix=f"Invoices/{invoice_month}/Service Invoices/"
    ):
        local_name = obj.key.split("/")[-1]
        s3_invoice_list.append(local_name)
        invoice_bucket.download_file(obj.key, local_name)

    return s3_invoice_list


def merge_csv(files):
    """Merge multiple CSV files and return a single pandas dataframe"""
    dataframes = []
    for file in files:
        dataframe = pandas.read_csv(
            file,
            dtype={
                COST_FIELD: pandas.ArrowDtype(pyarrow.decimal128(12, 2)),
                RATE_FIELD: str,
            },
        )
        dataframes.append(dataframe)

    merged_dataframe = pandas.concat(dataframes, ignore_index=True)
    merged_dataframe.reset_index(drop=True, inplace=True)
    return merged_dataframe


def get_invoice_date(dataframe):
    """Returns the invoice date as a pandas timestamp object

    Note that it only checks the first entry because it should
    be the same for every row.
    """
    invoice_date_str = dataframe[INVOICE_DATE_FIELD][0]
    invoice_date = pandas.to_datetime(invoice_date_str, format="%Y-%m")
    return invoice_date


def timed_projects(timed_projects_file, invoice_date):
    """Returns list of projects that should be excluded based on dates"""
    dataframe = pandas.read_csv(timed_projects_file)

    # convert to pandas timestamp objects
    dataframe["Start Date"] = pandas.to_datetime(
        dataframe["Start Date"], format="%Y-%m"
    )
    dataframe["End Date"] = pandas.to_datetime(dataframe["End Date"], format="%Y-%m")

    mask = (dataframe["Start Date"] <= invoice_date) & (
        invoice_date <= dataframe["End Date"]
    )
    return dataframe[mask]["Project"].to_list()


def backup_to_s3_old_pi_file(old_pi_file):
    invoice_bucket = util.get_invoice_bucket()
    invoice_bucket.upload_file(old_pi_file, f"PIs/Archive/PI {get_iso8601_time()}.csv")


def export_billables(dataframe, output_file):
    dataframe.to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
