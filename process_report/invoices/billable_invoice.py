from dataclasses import dataclass
from decimal import Decimal
import logging
import sys

import pandas
import pyarrow

import process_report.invoices.invoice as invoice
import process_report.util as util


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class BillableInvoice(invoice.Invoice):
    NEW_PI_CREDIT_CODE = "0002"
    INITIAL_CREDIT_AMOUNT = 1000
    EXCLUDE_SU_TYPES = ["OpenShift GPUA100SXM4", "OpenStack GPUA100SXM4"]
    PI_S3_FILEPATH = "PIs/PI.csv"

    nonbillable_pis: list[str]
    nonbillable_projects: list[str]
    old_pi_filepath: str

    @staticmethod
    def _load_old_pis(old_pi_filepath) -> pandas.DataFrame:
        try:
            old_pi_df = pandas.read_csv(
                old_pi_filepath,
                dtype={
                    invoice.PI_INITIAL_CREDITS: pandas.ArrowDtype(
                        pyarrow.decimal128(21, 2)
                    ),
                    invoice.PI_1ST_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                    invoice.PI_2ND_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                },
            )
        except FileNotFoundError:
            sys.exit("Applying credit 0002 failed. Old PI file does not exist")

        return old_pi_df

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

    @staticmethod
    def _validate_pi_names(data: pandas.DataFrame):
        invalid_pi_projects = data[pandas.isna(data[invoice.PI_FIELD])]
        for i, row in invalid_pi_projects.iterrows():
            logger.warn(
                f"Billable project {row[invoice.PROJECT_FIELD]} has empty PI field"
            )
        return data[~pandas.isna(data[invoice.PI_FIELD])]

    @staticmethod
    def _get_pi_age(old_pi_df: pandas.DataFrame, pi, invoice_month):
        """Returns time difference between current invoice month and PI's first invoice month
        I.e 0 for new PIs
        Will raise an error if the PI'a age is negative, which suggests a faulty invoice, or a program bug"""
        first_invoice_month = old_pi_df.loc[
            old_pi_df[invoice.PI_PI_FIELD] == pi, invoice.PI_FIRST_MONTH
        ]
        if first_invoice_month.empty:
            return 0

        month_diff = util.get_month_diff(invoice_month, first_invoice_month.iat[0])
        if month_diff < 0:
            sys.exit(
                f"PI {pi} from {first_invoice_month} found in {invoice_month} invoice!"
            )
        else:
            return month_diff

    def _prepare(self):
        self.data = self._remove_nonbillables(
            self.data, self.nonbillable_pis, self.nonbillable_projects
        )
        self.data = self._validate_pi_names(self.data)
        self.data[invoice.CREDIT_FIELD] = None
        self.data[invoice.CREDIT_CODE_FIELD] = None
        self.data[invoice.BALANCE_FIELD] = Decimal(0)
        self.old_pi_df = self._load_old_pis(self.old_pi_filepath)

    def _process(self):
        self.data, self.updated_old_pi_df = self._apply_credits_new_pi(
            self.data, self.old_pi_df
        )

    def _prepare_export(self):
        self.updated_old_pi_df = self.updated_old_pi_df.astype(
            {
                invoice.PI_INITIAL_CREDITS: pandas.ArrowDtype(
                    pyarrow.decimal128(21, 2)
                ),
                invoice.PI_1ST_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
                invoice.PI_2ND_USED: pandas.ArrowDtype(pyarrow.decimal128(21, 2)),
            },
        )

    def export(self):
        super().export()
        self.old_pi_df.to_csv(self.old_pi_filepath, index=False)

    def export_s3(self, s3_bucket):
        super().export_s3(s3_bucket)
        s3_bucket.upload_file(self.old_pi_filepath, self.PI_S3_FILEPATH)

    def _apply_credits_new_pi(
        self, data: pandas.DataFrame, old_pi_df: pandas.DataFrame
    ):
        def get_initial_credit_amount(
            old_pi_df, invoice_month, default_initial_credit_amount
        ):
            first_month_processed_pis = old_pi_df[
                old_pi_df[invoice.PI_FIRST_MONTH] == invoice_month
            ]
            if first_month_processed_pis[
                invoice.PI_INITIAL_CREDITS
            ].empty or pandas.isna(
                new_pi_credit_amount := first_month_processed_pis[
                    invoice.PI_INITIAL_CREDITS
                ].iat[0]
            ):
                new_pi_credit_amount = default_initial_credit_amount

            return new_pi_credit_amount

        new_pi_credit_amount = get_initial_credit_amount(
            old_pi_df, self.invoice_month, self.INITIAL_CREDIT_AMOUNT
        )
        print(f"New PI Credit set at {new_pi_credit_amount} for {self.invoice_month}")

        current_pi_set = set(data[invoice.PI_FIELD])
        for pi in current_pi_set:
            pi_projects = data[data[invoice.PI_FIELD] == pi]
            pi_age = self._get_pi_age(old_pi_df, pi, self.invoice_month)
            pi_old_pi_entry = old_pi_df.loc[
                old_pi_df[invoice.PI_PI_FIELD] == pi
            ].squeeze()

            if pi_age > 1:
                for i, row in pi_projects.iterrows():
                    data.at[i, invoice.BALANCE_FIELD] = row[invoice.COST_FIELD]
            else:
                if pi_age == 0:
                    if len(pi_old_pi_entry) == 0:
                        pi_entry = [pi, self.invoice_month, new_pi_credit_amount, 0, 0]
                        old_pi_df = pandas.concat(
                            [
                                pandas.DataFrame([pi_entry], columns=old_pi_df.columns),
                                old_pi_df,
                            ],
                            ignore_index=True,
                        )
                        pi_old_pi_entry = old_pi_df.loc[
                            old_pi_df[invoice.PI_PI_FIELD] == pi
                        ].squeeze()

                    remaining_credit = new_pi_credit_amount
                    credit_used_field = invoice.PI_1ST_USED
                elif pi_age == 1:
                    remaining_credit = (
                        pi_old_pi_entry[invoice.PI_INITIAL_CREDITS]
                        - pi_old_pi_entry[invoice.PI_1ST_USED]
                    )
                    credit_used_field = invoice.PI_2ND_USED

                initial_credit = remaining_credit
                for i, row in pi_projects.iterrows():
                    if (
                        remaining_credit == 0
                        or row[invoice.SU_TYPE_FIELD] in self.EXCLUDE_SU_TYPES
                    ):
                        data.at[i, invoice.BALANCE_FIELD] = row[invoice.COST_FIELD]
                    else:
                        project_cost = row[invoice.COST_FIELD]
                        applied_credit = min(project_cost, remaining_credit)

                        data.at[i, invoice.CREDIT_FIELD] = applied_credit
                        data.at[i, invoice.CREDIT_CODE_FIELD] = self.NEW_PI_CREDIT_CODE
                        data.at[i, invoice.BALANCE_FIELD] = (
                            row[invoice.COST_FIELD] - applied_credit
                        )
                        remaining_credit -= applied_credit

                credits_used = initial_credit - remaining_credit
                if (pi_old_pi_entry[credit_used_field] != 0) and (
                    credits_used != pi_old_pi_entry[credit_used_field]
                ):
                    print(
                        f"Warning: PI file overwritten. PI {pi} previously used ${pi_old_pi_entry[credit_used_field]} of New PI credits, now uses ${credits_used}"
                    )
                old_pi_df.loc[
                    old_pi_df[invoice.PI_PI_FIELD] == pi, credit_used_field
                ] = credits_used

        return (data, old_pi_df)
