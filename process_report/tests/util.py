import pandas

from process_report.invoices import billable_invoice, bu_internal_invoice


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


def new_bu_internal_invoice(
    name="", invoice_month="0000-00", data=pandas.DataFrame(), subsidy_amount=0
):
    return bu_internal_invoice.BUInternalInvoice(
        name, invoice_month, data, subsidy_amount
    )
