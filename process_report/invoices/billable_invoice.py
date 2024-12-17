from dataclasses import dataclass
import logging

import pandas
import pyarrow

from process_report.invoices import invoice

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class BillableInvoice(invoice.Invoice):
    """
    This invoice operates on data processed by these Processors:
    - ValidateBillablePIsProcessor
    - NewPICreditProcessor
    """

    PI_S3_FILEPATH = "PIs/PI.csv"

    old_pi_filepath: str
    updated_old_pi_df: pandas.DataFrame

    export_columns_list = [
        invoice.INVOICE_DATE_FIELD,
        invoice.PROJECT_FIELD,
        invoice.PROJECT_ID_FIELD,
        invoice.PI_FIELD,
        invoice.INVOICE_EMAIL_FIELD,
        invoice.INVOICE_ADDRESS_FIELD,
        invoice.INSTITUTION_FIELD,
        invoice.INSTITUTION_ID_FIELD,
        invoice.SU_HOURS_FIELD,
        invoice.SU_TYPE_FIELD,
        invoice.RATE_FIELD,
        invoice.COST_FIELD,
        invoice.CREDIT_FIELD,
        invoice.CREDIT_CODE_FIELD,
        invoice.BALANCE_FIELD,
    ]

    def _prepare_export(self):
        self.export_data = self.data[
            self.data[invoice.IS_BILLABLE_FIELD] & ~self.data[invoice.MISSING_PI_FIELD]
        ]
        self.updated_old_pi_df = self.updated_old_pi_df.astype(
            {
                invoice.PI_INITIAL_CREDITS: pandas.ArrowDtype(
                    pyarrow.decimal128(21, 2)
                ),
                invoice.PI_1ST_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                invoice.PI_2ND_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            },
        )

    def export(self):
        super().export()
        self.updated_old_pi_df.to_csv(self.old_pi_filepath, index=False)

    def export_s3(self, s3_bucket):
        super().export_s3(s3_bucket)
        s3_bucket.upload_file(self.old_pi_filepath, self.PI_S3_FILEPATH)
