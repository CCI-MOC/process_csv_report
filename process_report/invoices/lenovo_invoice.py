from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class LenovoInvoice(invoice.Invoice):
    LENOVO_SU_TYPES = ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"]
    SU_CHARGE_MULTIPLIER = 1

    def _prepare(self):
        self.data = self.data[
            self.data[invoice.SU_TYPE_FIELD].isin(self.LENOVO_SU_TYPES)
        ][
            [
                invoice.INVOICE_DATE_FIELD,
                invoice.PROJECT_FIELD,
                invoice.INSTITUTION_FIELD,
                invoice.SU_HOURS_FIELD,
                invoice.SU_TYPE_FIELD,
            ]
        ].copy()

        self.data.rename(columns={invoice.SU_HOURS_FIELD: "SU Hours"}, inplace=True)
        self.data.insert(len(self.data.columns), "SU Charge", self.SU_CHARGE_MULTIPLIER)

    def _process(self):
        self.data["Charge"] = self.data["SU Hours"] * self.data["SU Charge"]
