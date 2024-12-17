from process_report.invoices import invoice
import process_report.util as util


class MOCAPrepaidInvoice(invoice.Invoice):
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
        invoice.GROUP_NAME_FIELD,
        invoice.GROUP_INSTITUTION_FIELD,
        invoice.GROUP_BALANCE_FIELD,
        invoice.COST_FIELD,
        invoice.GROUP_BALANCE_USED_FIELD,
        invoice.CREDIT_FIELD,
        invoice.CREDIT_CODE_FIELD,
        invoice.BALANCE_FIELD,
    ]

    @property
    def output_path(self) -> str:
        return f"MOCA-A_Prepaid_Groups-{self.invoice_month}-Invoice.csv"

    @property
    def output_s3_key(self) -> str:
        return f"Invoices/{self.invoice_month}/MOCA-A_Prepaid_Groups-{self.invoice_month}-Invoice.csv"

    @property
    def output_s3_archive_key(self):
        return f"Invoices/{self.invoice_month}/Archive/MOCA-A_Prepaid_Groups-{self.invoice_month}-Invoice {util.get_iso8601_time()}.csv"

    def _prepare_export(self):
        self.data = self.data[self.data[invoice.GROUP_MANAGED_FIELD] == False]  # noqa: E712
