from dataclasses import dataclass
from decimal import Decimal

import process_report.invoices.invoice as invoice
import process_report.invoices.discount_invoice as discount_invoice


@dataclass
class BUInternalInvoice(discount_invoice.DiscountInvoice):
    subsidy_amount: int

    def _prepare(self):
        def get_project(row):
            project_alloc = row[invoice.PROJECT_FIELD]
            if project_alloc.rfind("-") == -1:
                return project_alloc
            else:
                return project_alloc[: project_alloc.rfind("-")]

        self.data = self.data[
            self.data[invoice.INSTITUTION_FIELD] == "Boston University"
        ].copy()
        self.data["Project"] = self.data.apply(get_project, axis=1)
        self.data[invoice.SUBSIDY_FIELD] = Decimal(0)
        self.data = self.data[
            [
                invoice.INVOICE_DATE_FIELD,
                invoice.PI_FIELD,
                "Project",
                invoice.COST_FIELD,
                invoice.CREDIT_FIELD,
                invoice.SUBSIDY_FIELD,
                invoice.BALANCE_FIELD,
            ]
        ]

    def _process(self):
        data_summed_projects = self._sum_project_allocations(self.data)
        self.data = self._apply_subsidy(data_summed_projects, self.subsidy_amount)

    def _sum_project_allocations(self, dataframe):
        """A project may have multiple allocations, and therefore multiple rows
        in the raw invoices. For BU-Internal invoice, we only want 1 row for
        each unique project, summing up its allocations' costs"""
        project_list = dataframe["Project"].unique()
        data_no_dup = dataframe.drop_duplicates("Project", inplace=False)
        sum_fields = [invoice.COST_FIELD, invoice.CREDIT_FIELD, invoice.BALANCE_FIELD]
        for project in project_list:
            project_mask = dataframe["Project"] == project
            no_dup_project_mask = data_no_dup["Project"] == project

            sum_fields_sums = dataframe[project_mask][sum_fields].sum().values
            data_no_dup.loc[no_dup_project_mask, sum_fields] = sum_fields_sums

        return data_no_dup

    def _apply_subsidy(self, dataframe, subsidy_amount):
        pi_list = dataframe[invoice.PI_FIELD].unique()

        for pi in pi_list:
            pi_projects = dataframe[dataframe[invoice.PI_FIELD] == pi]
            self.apply_flat_discount(
                dataframe,
                pi_projects,
                subsidy_amount,
                invoice.SUBSIDY_FIELD,
                invoice.BALANCE_FIELD,
            )

        return dataframe
