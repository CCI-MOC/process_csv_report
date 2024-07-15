from dataclasses import dataclass

import process_report.invoices.invoice as invoice
import process_report.util as util


@dataclass
class HUBUInvoice(invoice.Invoice):
    @property
    def output_s3_key(self) -> str:
        return (
            f"Invoices/{self.invoice_month}/NERC-{self.invoice_month}-Total-Invoice.csv"
        )

    @property
    def output_s3_archive_key(self):
        return f"Invoices/{self.invoice_month}/Archive/NERC-{self.invoice_month}-Total-Invoice {util.get_iso8601_time()}.csv"

    def _prepare_export(self):
        self.data = self.data[
            (self.data[invoice.INSTITUTION_FIELD] == "Harvard University")
            | (self.data[invoice.INSTITUTION_FIELD] == "Boston University")
        ].copy()
