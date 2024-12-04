from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class LenovoInvoice(invoice.Invoice):
    LENOVO_SU_TYPES = ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"]

    export_columns_list = [
        invoice.INVOICE_DATE_FIELD,
        invoice.PROJECT_FIELD,
        invoice.INSTITUTION_FIELD,
        invoice.SU_HOURS_FIELD,
        invoice.SU_TYPE_FIELD,
        invoice.SU_CHARGE_FIELD,
        invoice.LENOVO_CHARGE_FIELD,
    ]
    exported_columns_map = {invoice.SU_HOURS_FIELD: "SU Hours"}

    def _prepare_export(self):
        self.export_data = self.data[
            self.data[invoice.SU_TYPE_FIELD].isin(self.LENOVO_SU_TYPES)
        ]
