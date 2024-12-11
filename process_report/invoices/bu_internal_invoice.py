from dataclasses import dataclass

import process_report.invoices.invoice as invoice


@dataclass
class BUInternalInvoice(invoice.Invoice):
    """
    This invoice operates on data processed by these Processors:
    - ValidateBillablePIsProcessor
    - NewPICreditProcessor
    """

    export_columns_list = [
        invoice.INVOICE_DATE_FIELD,
        invoice.PI_FIELD,
        "Project",
        invoice.COST_FIELD,
        invoice.CREDIT_FIELD,
        invoice.SUBSIDY_FIELD,
        invoice.PI_BALANCE_FIELD,
    ]

    exported_columns_map = {invoice.PI_BALANCE_FIELD: "Balance"}

    def _prepare_export(self):
        self.export_data = self.data[
            self.data[invoice.IS_BILLABLE_FIELD] & ~self.data[invoice.MISSING_PI_FIELD]
        ]
        self.export_data = self.export_data[
            self.export_data[invoice.INSTITUTION_FIELD] == "Boston University"
        ]
        self.export_data = self._sum_project_allocations(self.export_data)

    def _sum_project_allocations(self, dataframe):
        """A project may have multiple allocations, and therefore multiple rows
        in the raw invoices. For BU-Internal invoice, we only want 1 row for
        each unique project, summing up its allocations' costs"""
        project_list = dataframe["Project"].unique()
        data_no_dup = dataframe.drop_duplicates("Project", inplace=False)
        sum_fields = [
            invoice.COST_FIELD,
            invoice.CREDIT_FIELD,
            invoice.SUBSIDY_FIELD,
            invoice.PI_BALANCE_FIELD,
        ]
        for project in project_list:
            project_mask = dataframe["Project"] == project
            no_dup_project_mask = data_no_dup["Project"] == project

            sum_fields_sums = dataframe[project_mask][sum_fields].sum().values
            data_no_dup.loc[no_dup_project_mask, sum_fields] = sum_fields_sums

        return data_no_dup
