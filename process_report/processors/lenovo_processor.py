from dataclasses import dataclass


from process_report.invoices import invoice
from process_report.processors import processor


@dataclass
class LenovoProcessor(processor.Processor):
    SU_CHARGE_MULTIPLIER = 1

    def _process(self):
        self.data[invoice.SU_CHARGE_FIELD] = self.SU_CHARGE_MULTIPLIER
        self.data[invoice.LENOVO_CHARGE_FIELD] = (
            self.data[invoice.SU_HOURS_FIELD] * self.data[invoice.SU_CHARGE_FIELD]
        )
