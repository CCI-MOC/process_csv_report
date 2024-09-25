from dataclasses import dataclass

import pandas

from process_report.invoices import invoice
from process_report.processors import processor


@dataclass
class RemoveNonbillables(processor.Processor):
    nonbillable_pis: list[str]
    nonbillable_projects: list[str]

    @staticmethod
    def _remove_nonbillables(
        data: pandas.DataFrame,
        nonbillable_pis: list[str],
        nonbillable_projects: list[str],
    ):
        return data[
            ~data[invoice.PI_FIELD].isin(nonbillable_pis)
            & ~data[invoice.PROJECT_FIELD].isin(nonbillable_projects)
        ]

    def _process(self):
        self.data = self._remove_nonbillables(
            self.data, self.nonbillable_pis, self.nonbillable_projects
        )
