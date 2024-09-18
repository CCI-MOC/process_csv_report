from dataclasses import dataclass

from process_report.invoices import invoice


@dataclass
class Processor(invoice.Invoice):
    pass
