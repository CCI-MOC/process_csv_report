import os
from dataclasses import dataclass

import pandas

import process_report.invoices.invoice as invoice
import process_report.util as util


@dataclass
class PIInvoice(invoice.Invoice):
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

    def _prepare(self):
        self.pi_list = self.data[invoice.PI_FIELD].unique()

    def export(self):
        def _export_pi_invoice(pi):
            if pandas.isna(pi):
                return
            pi_projects = export_data[export_data[invoice.PI_FIELD] == pi]
            pi_instituition = pi_projects[invoice.INSTITUTION_FIELD].iat[0]
            pi_projects.to_csv(
                f"{self.name}/{pi_instituition}_{pi} {self.invoice_month}.csv"
            )

        export_data = self._filter_columns()
        if not os.path.exists(
            self.name
        ):  # self.name is name of folder storing invoices
            os.mkdir(self.name)

        for pi in self.pi_list:
            _export_pi_invoice(pi)

    def export_s3(self, s3_bucket):
        def _export_s3_pi_invoice(pi_invoice):
            pi_invoice_path = os.path.join(self.name, pi_invoice)
            striped_invoice_path = os.path.splitext(pi_invoice_path)[0]
            output_s3_path = f"Invoices/{self.invoice_month}/{striped_invoice_path}.csv"
            output_s3_archive_path = f"Invoices/{self.invoice_month}/Archive/{striped_invoice_path} {util.get_iso8601_time()}.csv"
            s3_bucket.upload_file(pi_invoice_path, output_s3_path)
            s3_bucket.upload_file(pi_invoice_path, output_s3_archive_path)

        for pi_invoice in os.listdir(self.name):
            _export_s3_pi_invoice(pi_invoice)
