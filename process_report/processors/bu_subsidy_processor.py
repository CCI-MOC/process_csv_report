from dataclasses import dataclass
from decimal import Decimal

from process_report.invoices import invoice
from process_report.processors import discount_processor


@dataclass
class BUSubsidyProcessor(discount_processor.DiscountProcessor):
    IS_DISCOUNT_BY_NERC = False

    subsidy_amount: int

    def _prepare(self):
        def get_project(row):
            project_alloc = row[invoice.PROJECT_FIELD]
            if project_alloc.rfind("-") == -1:
                return project_alloc
            else:
                return project_alloc[: project_alloc.rfind("-")]

        self.data[invoice.PROJECT_NAME_FIELD] = self.data.apply(get_project, axis=1)
        self.data[invoice.SUBSIDY_FIELD] = Decimal(0)

    def _process(self):
        self.data = self._apply_subsidy(self.data, self.subsidy_amount)

    @staticmethod
    def _get_subsidy_eligible_projects(data):
        filtered_data = data[
            data[invoice.IS_BILLABLE_FIELD] & ~data[invoice.MISSING_PI_FIELD]
        ]
        filtered_data = filtered_data[
            filtered_data[invoice.INSTITUTION_FIELD] == "Boston University"
        ].copy()

        return filtered_data

    def _apply_subsidy(self, dataframe, subsidy_amount):
        subsidy_eligible_projects = self._get_subsidy_eligible_projects(dataframe)
        pi_list = subsidy_eligible_projects[invoice.PI_FIELD].unique()

        for pi in pi_list:
            pi_projects = subsidy_eligible_projects[
                subsidy_eligible_projects[invoice.PI_FIELD] == pi
            ]
            self.apply_flat_discount(
                dataframe,
                pi_projects,
                invoice.PI_BALANCE_FIELD,
                subsidy_amount,
                invoice.SUBSIDY_FIELD,
                invoice.BALANCE_FIELD,
            )

        return dataframe
