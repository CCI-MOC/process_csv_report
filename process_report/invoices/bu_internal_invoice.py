from dataclasses import dataclass
from decimal import Decimal

import process_report.invoices.invoice as invoice


@dataclass
class BUInternalInvoice(invoice.Invoice):
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
        project_list = self.data["Project"].unique()
        data_no_dup = self.data.drop_duplicates("Project", inplace=False)
        sum_fields = [invoice.COST_FIELD, invoice.CREDIT_FIELD, invoice.BALANCE_FIELD]
        for project in project_list:
            project_mask = self.data["Project"] == project
            no_dup_project_mask = data_no_dup["Project"] == project

            sum_fields_sums = self.data[project_mask][sum_fields].sum().values
            data_no_dup.loc[no_dup_project_mask, sum_fields] = sum_fields_sums

        self.data = self._apply_subsidy(data_no_dup, self.subsidy_amount)

    def _apply_subsidy(self, dataframe, subsidy_amount):
        pi_list = dataframe[invoice.PI_FIELD].unique()

        for pi in pi_list:
            pi_projects = dataframe[dataframe[invoice.PI_FIELD] == pi]
            remaining_subsidy = subsidy_amount
            for i, row in pi_projects.iterrows():
                project_remaining_cost = row[invoice.BALANCE_FIELD]
                applied_subsidy = min(project_remaining_cost, remaining_subsidy)

                dataframe.at[i, invoice.SUBSIDY_FIELD] = applied_subsidy
                dataframe.at[i, invoice.BALANCE_FIELD] = (
                    row[invoice.BALANCE_FIELD] - applied_subsidy
                )
                remaining_subsidy -= applied_subsidy

                if remaining_subsidy == 0:
                    break

        return dataframe
