from dataclasses import dataclass

import process_report.invoices.invoice as invoice
import process_report.util as util


@dataclass
class NERCTotalInvoice(invoice.Invoice):
    """
    This invoice operates on data processed by these Processors:
    - ValidateBillablePIsProcessor
    - NewPICreditProcessor
    """

    INCLUDED_INSTITUTIONS = [
        "Harvard University",
        "Boston University",
        "University of Rhode Island",
    ]

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

    @property
    def output_path(self) -> str:
        return f"NERC-{self.invoice_month}-Total-Invoice.csv"

    @property
    def output_s3_key(self) -> str:
        return (
            f"Invoices/{self.invoice_month}/NERC-{self.invoice_month}-Total-Invoice.csv"
        )

    @property
    def output_s3_archive_key(self):
        return f"Invoices/{self.invoice_month}/Archive/NERC-{self.invoice_month}-Total-Invoice {util.get_iso8601_time()}.csv"

    def _prepare_export(self):
        self.export_data = self.data[
            self.data[invoice.IS_BILLABLE_FIELD] & ~self.data[invoice.MISSING_PI_FIELD]
        ]
        self.export_data = self.export_data[
            self.export_data[invoice.INSTITUTION_FIELD].isin(self.INCLUDED_INSTITUTIONS)
        ].copy()
