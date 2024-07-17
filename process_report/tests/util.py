import pandas

from process_report.invoices import billable_invoice, pi_specific_invoice


def new_billable_invoice(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
    nonbillable_pis=[],
    nonbillable_projects=[],
    old_pi_filepath="",
):
    return billable_invoice.BillableInvoice(
        name,
        invoice_month,
        data,
        nonbillable_pis,
        nonbillable_projects,
        old_pi_filepath,
    )


def new_pi_specific_invoice(
    name="",
    invoice_month="0000-00",
    data=pandas.DataFrame(),
):
    return pi_specific_invoice.PIInvoice(
        name,
        invoice_month,
        data,
    )
