import os
from unittest import TestCase
import tempfile
import pandas

from process_report.tests import util as test_utils


class TestPrepaymentProcessor(TestCase):
    def _assert_result_invoice(
        self,
        test_invoice,
        test_prepay_credits,
        test_prepay_debits_filepath,
        test_prepay_projects,
        test_prepay_contacts,
        answer_invoice,
        answer_prepay_debits,
        invoice_month="0000-00",
    ):
        new_prepayment_proc = test_utils.new_prepayment_processor(
            "",
            invoice_month,
            test_invoice,
            test_prepay_credits,
            test_prepay_debits_filepath,
            test_prepay_projects,
            test_prepay_contacts,
        )
        new_prepayment_proc.process()
        output_invoice = new_prepayment_proc.data
        output_prepay_debits = new_prepayment_proc.prepay_debits.sort_values(
            by="Month", ignore_index=True
        )

        answer_invoice = answer_invoice.astype(output_invoice.dtypes)
        answer_prepay_debits = answer_prepay_debits.astype(
            output_prepay_debits.dtypes
        ).sort_values(by="Month", ignore_index=True)

        self.assertTrue(output_invoice.equals(answer_invoice))
        self.assertTrue(output_prepay_debits.equals(answer_prepay_debits))

    def _get_test_invoice(self, project_names, pi_balances, balances=None):
        if not balances:
            balances = pi_balances

        return pandas.DataFrame(
            {
                "Project": project_names,
                "PI Balance": pi_balances,
                "Balance": balances,
                "Invoice Email": [None] * len(project_names),
            }
        )

    def _get_test_prepay_credits(self, months, group_names, credits):
        return pandas.DataFrame(
            {"Month": months, "Group Name": group_names, "Credit": credits}
        )

    def _get_test_prepay_debits(self, months, group_names, debits):
        return pandas.DataFrame(
            {"Month": months, "Group Name": group_names, "Debit": debits}
        )

    def _get_test_prepay_projects(
        self, group_names, project_names, start_dates, end_dates
    ):
        return pandas.DataFrame(
            {
                "Group Name": group_names,
                "Project": project_names,
                "Start Date": start_dates,
                "End Date": end_dates,
            }
        )

    def _get_test_prepay_contacts(self, group_names, emails, is_managed):
        return pandas.DataFrame(
            {
                "Group Name": group_names,
                "Group Contact Email": emails,
                "MGHPCC Managed": is_managed,
            }
        )

    def setUp(self) -> None:
        self.test_prepay_debits_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", suffix=".csv"
        )

    def tearDown(self) -> None:
        os.remove(self.test_prepay_debits_file.name)

    def test_one_group_one_project(self):
        """Simple one project test and checks idempotentcy"""
        invoice_month = "2024-10"
        test_invoice = self._get_test_invoice(["P1"], [1000])
        test_prepay_credits = self._get_test_prepay_credits(["2024-01"], ["G1"], [1500])
        test_prepay_debits = self._get_test_prepay_debits([], [], [])
        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        test_prepay_projects = self._get_test_prepay_projects(
            ["G1"], ["P1"], ["2024-09"], ["2024-12"]
        )
        test_prepay_contacts = self._get_test_prepay_contacts(
            ["G1"], ["G1@bu.edu"], [True]
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Prepaid Group Name"] = ["G1"]
        answer_invoice["Prepaid Group Institution"] = ["Boston University"]
        answer_invoice["MGHPCC Managed"] = [True]
        answer_invoice["Prepaid Group Balance"] = [500]
        answer_invoice["Prepaid Group Used"] = [1000]
        answer_invoice["Invoice Email"] = ["G1@bu.edu"]
        answer_invoice["PI Balance"] = [0]
        answer_invoice["Balance"] = [0]

        answer_prepay_debits = self._get_test_prepay_debits(
            [invoice_month], ["G1"], [1000]
        )

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # Is the output invoice and debits the same if
        # processor is ran twice with same invoice but updated debits?
        self._assert_result_invoice(
            test_invoice,
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

    def test_project_active_periods(self):
        """How is prepay handled for 2 projects in same group in different billing months?"""
        # Prepay projects not in active period
        project_names = ["P1", "P2"]

        invoice_month = "2024-06"
        test_invoice = self._get_test_invoice(project_names, [1000, 2000])
        test_prepay_credits = self._get_test_prepay_credits(["2024-04"], ["G1"], [5000])
        test_prepay_debits = self._get_test_prepay_debits([], [], [])
        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        test_prepay_projects = self._get_test_prepay_projects(
            ["G1", "G1"], project_names, ["2024-08", "2024-10"], ["2024-12", "2025-02"]
        )
        test_prepay_contacts = self._get_test_prepay_contacts(
            ["G1"], ["G1@bu.edu"], [True]
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Prepaid Group Name"] = [None, None]
        answer_invoice["Prepaid Group Institution"] = [None, None]
        answer_invoice["MGHPCC Managed"] = [None, None]
        answer_invoice["Prepaid Group Balance"] = [None, None]
        answer_invoice["Prepaid Group Used"] = [None, None]

        answer_prepay_debits = test_prepay_debits.copy()

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # One project in active period
        invoice_month = "2024-08"
        answer_invoice["Prepaid Group Name"] = ["G1", None]
        answer_invoice["Prepaid Group Institution"] = ["Boston University", None]
        answer_invoice["MGHPCC Managed"] = [True, None]
        answer_invoice["Prepaid Group Balance"] = [4000, None]
        answer_invoice["Prepaid Group Used"] = [1000, None]
        answer_invoice["Invoice Email"] = ["G1@bu.edu", None]
        answer_invoice["PI Balance"] = [0, 2000]
        answer_invoice["Balance"] = [0, 2000]

        test_prepay_debits.to_csv(
            self.test_prepay_debits_file.name, index=False
        )  # Resetting debit file
        answer_prepay_debits = self._get_test_prepay_debits(
            [invoice_month], ["G1"], [1000]
        )

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # Both projects in active period
        invoice_month = "2024-12"
        answer_invoice["Prepaid Group Name"] = ["G1", "G1"]
        answer_invoice["Prepaid Group Institution"] = [
            "Boston University",
            "Boston University",
        ]
        answer_invoice["MGHPCC Managed"] = [True, True]
        answer_invoice["Prepaid Group Balance"] = [2000, 2000]
        answer_invoice["Prepaid Group Used"] = [1000, 2000]
        answer_invoice["Invoice Email"] = ["G1@bu.edu", "G1@bu.edu"]
        answer_invoice["PI Balance"] = [0, 0]
        answer_invoice["Balance"] = [0, 0]

        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        answer_prepay_debits = self._get_test_prepay_debits(
            [invoice_month], ["G1"], [3000]
        )

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # Both projects in active period, but before credits were given
        test_prepay_credits = self._get_test_prepay_credits(["2026-04"], ["G1"], [5000])

        # Still has group info, but group balance should be 0
        answer_invoice["Prepaid Group Balance"] = [0, 0]
        answer_invoice["Prepaid Group Used"] = [None, None]
        answer_invoice["PI Balance"] = [1000, 2000]
        answer_invoice["Balance"] = [1000, 2000]

        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        answer_prepay_debits = self._get_test_prepay_debits([], [], [])

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

    def test_one_group_two_project_balances(self):
        """Different scenarios for 2 projects' balances"""
        # Prepayment partially covers projects
        project_names = ["P1", "P2"]

        invoice_month = "2024-10"
        test_invoice = self._get_test_invoice(project_names, [1000, 2000])
        test_prepay_credits = self._get_test_prepay_credits(["2024-04"], ["G1"], [1500])
        test_prepay_debits = self._get_test_prepay_debits([], [], [])
        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        test_prepay_projects = self._get_test_prepay_projects(
            ["G1", "G1"], project_names, ["2024-08", "2024-08"], ["2024-10", "2025-02"]
        )
        test_prepay_contacts = self._get_test_prepay_contacts(
            ["G1"], ["G1@bu.edu"], [True]
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Prepaid Group Name"] = ["G1", "G1"]
        answer_invoice["Prepaid Group Institution"] = [
            "Boston University",
            "Boston University",
        ]
        answer_invoice["MGHPCC Managed"] = [True, True]
        answer_invoice["Prepaid Group Balance"] = [0, 0]
        answer_invoice["Prepaid Group Used"] = [1000, 500]
        answer_invoice["Invoice Email"] = ["G1@bu.edu", "G1@bu.edu"]
        answer_invoice["PI Balance"] = [0, 1500]
        answer_invoice["Balance"] = [0, 1500]

        answer_prepay_debits = self._get_test_prepay_debits(
            [invoice_month], ["G1"], [1500]
        )

        self._assert_result_invoice(
            test_invoice,
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # PI balance != Balance
        test_invoice = self._get_test_invoice(project_names, [1000, 2000], [2000, 2500])

        answer_invoice["Balance"] = [1000, 2000]

        self._assert_result_invoice(
            test_invoice,
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

    def test_two_group_one_project(self):
        """How is prepay handled for two different groups with different credits and debits?"""
        # Invoice month is before any credits are given
        project_names = ["G1P1", "G2P1"]

        invoice_month = "2024-03"
        test_invoice = self._get_test_invoice(project_names, [1000, 2000])
        test_prepay_credits = self._get_test_prepay_credits(
            ["2024-04", "2024-04", "2024-06", "2024-08", "2024-10"],
            ["G1", "G2", "G1", "G2", "G1"],
            [700, 800, 1000, 2000, 3500],
        )
        test_prepay_debits = self._get_test_prepay_debits(
            ["2024-05", "2024-06", "2024-07", "2024-10"],
            ["G1", "G2", "G2", "G1"],
            [200, 300, 1000, 2000],
        )
        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)
        test_prepay_projects = self._get_test_prepay_projects(
            ["G1", "G2"], project_names, ["2024-01", "2024-01"], ["2024-12", "2024-12"]
        )
        test_prepay_contacts = self._get_test_prepay_contacts(
            ["G1", "G2"], ["G1@bu.edu", "G2@harvard.edu"], [True, False]
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Prepaid Group Name"] = ["G1", "G2"]
        answer_invoice["Prepaid Group Institution"] = [
            "Boston University",
            "Harvard University",
        ]
        answer_invoice["MGHPCC Managed"] = [True, False]
        answer_invoice["Prepaid Group Balance"] = [0, 0]
        answer_invoice["Prepaid Group Used"] = [None, None]
        answer_invoice["Invoice Email"] = ["G1@bu.edu", "G2@harvard.edu"]

        answer_prepay_debits = test_prepay_debits.copy()

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # Invoice month is after some credits and debits are given
        invoice_month = "2024-08"
        answer_invoice["Prepaid Group Balance"] = [500, 0]
        answer_invoice["Prepaid Group Used"] = [1000, 1500]
        answer_invoice["PI Balance"] = [0, 500]
        answer_invoice["Balance"] = answer_invoice["PI Balance"]

        answer_prepay_debits = test_prepay_debits.copy()
        answer_prepay_debits = pandas.concat(
            [
                answer_prepay_debits,
                self._get_test_prepay_debits(
                    ["2024-08", "2024-08"], ["G1", "G2"], [1000, 1500]
                ),
            ],
            axis=0,
        ).sort_values("Month", ignore_index=True)

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

        # Invoice month after all credits and debits are given. Debit entry should overwritten
        invoice_month = "2024-10"
        # Reset the debit file as it has been edited from previous test case
        test_prepay_debits.to_csv(self.test_prepay_debits_file.name, index=False)

        answer_invoice["Prepaid Group Balance"] = [4000, 0]
        answer_invoice["Prepaid Group Used"] = [1000, 1500]
        answer_invoice["PI Balance"] = [0, 500]
        answer_invoice["Balance"] = answer_invoice["PI Balance"]

        answer_prepay_debits = self._get_test_prepay_debits(
            ["2024-05", "2024-06", "2024-07", "2024-10", "2024-10"],
            ["G1", "G2", "G2", "G1", "G2"],
            [200, 300, 1000, 1000, 1500],
        )

        self._assert_result_invoice(
            test_invoice.copy(),
            test_prepay_credits,
            self.test_prepay_debits_file.name,
            test_prepay_projects,
            test_prepay_contacts,
            answer_invoice,
            answer_prepay_debits,
            invoice_month,
        )

    def test_get_credit_snapshot(self):
        invoice_month = "2024-10"
        test_prepay_credits = self._get_test_prepay_credits(
            ["2024-10", "2024-10", "2024-10", "2024-09", "2024-09"],
            ["G1", "G2", "G3", "G1", "G2"],
            [0] * 5,
        )
        test_group_info_dict = {
            "G1": {"MGHPCC Managed": True},
            "G2": {"MGHPCC Managed": False},
            "G3": {"MGHPCC Managed": True},
        }
        answer_credits_snapshot = test_prepay_credits.iloc[[0, 2]]

        new_prepayment_proc = test_utils.new_prepayment_processor(
            invoice_month=invoice_month
        )
        new_prepayment_proc.prepay_credits = test_prepay_credits
        new_prepayment_proc.group_info_dict = test_group_info_dict
        output_snapshot = new_prepayment_proc._get_prepay_credits_snapshot()

        self.assertTrue(answer_credits_snapshot.equals(output_snapshot))
