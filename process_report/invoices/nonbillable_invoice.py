from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class NonbillableInvoice(invoice.Invoice):
    nonbillable_pis: list[str]
    nonbillable_projects: list[str]

    def _prepare_export(self):
        self.data = self.data[
            self.data[invoice.PI_FIELD].isin(self.nonbillable_pis)
            | self.data[invoice.PROJECT_FIELD].isin(self.nonbillable_projects)
        ]
