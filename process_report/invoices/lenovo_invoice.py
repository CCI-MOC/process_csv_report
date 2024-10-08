from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class LenovoInvoice(invoice.Invoice):
    LENOVO_SU_TYPES = ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"]
    SU_CHARGE_MULTIPLIER = 1

    export_columns_list = [
        invoice.INVOICE_DATE_FIELD,
        invoice.PROJECT_FIELD,
        invoice.INSTITUTION_FIELD,
        invoice.SU_HOURS_FIELD,
        invoice.SU_TYPE_FIELD,
        "SU Charge",
        "Charge",
    ]
    exported_columns_map = {invoice.SU_HOURS_FIELD: "SU Hours"}

    def _prepare(self):
        self.data["SU Charge"] = self.SU_CHARGE_MULTIPLIER

    def _process(self):
        self.data["Charge"] = self.data[invoice.SU_HOURS_FIELD] * self.data["SU Charge"]

    def _prepare_export(self):
        self.data = self.data[
            self.data[invoice.SU_TYPE_FIELD].isin(self.LENOVO_SU_TYPES)
        ]
