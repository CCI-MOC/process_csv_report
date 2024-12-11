from unittest import TestCase, mock
import tempfile
import pandas
import os
import uuid
import math
from textwrap import dedent

from process_report import process_report, util
from process_report.tests import util as test_utils


class TestGetInvoiceDate(TestCase):
    def test_get_invoice_date(self):
        # The month in sample data is not the same
        data = {"Invoice Month": ["2023-01", "2023-02", "2023-03"]}
        dataframe = pandas.DataFrame(data)

        invoice_date = process_report.get_invoice_date(dataframe)

        self.assertIsInstance(invoice_date, pandas.Timestamp)

        # Assert that the invoice_date is the first item
        expected_date = pandas.Timestamp("2023-01")
        self.assertEqual(invoice_date, expected_date)


class TestTimedProjects(TestCase):
    def setUp(self):
        # Without the dedent method, our data will have leading spaces which
        # messes up the first key. Also the '\' is imporant to ignore the first
        # new line we added so it's more readable in code.
        self.csv_data = dedent(
            """\
        Project,Start Date,End Date
        ProjectA,2022-09,2023-08
        ProjectB,2022-09,2023-09
        ProjectC,2023-09,2024-08
        ProjectD,2022-09,2024-08
        """
        )
        self.invoice_date = pandas.Timestamp("2023-09")

        self.csv_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        self.csv_file.write(self.csv_data)
        self.csv_file.close()

    def tearDown(self):
        os.remove(self.csv_file.name)

    def test_timed_projects(self):
        excluded_projects = process_report.timed_projects(
            self.csv_file.name, self.invoice_date
        )

        expected_projects = ["ProjectB", "ProjectC", "ProjectD"]
        self.assertEqual(excluded_projects, expected_projects)


class TestMergeCSV(TestCase):
    def setUp(self):
        self.header = ["ID", "Name", "Age"]
        self.data = [
            [1, "Alice", 25],
            [2, "Bob", 30],
            [3, "Charlie", 28],
        ]

        self.csv_files = []

        for _ in range(3):
            csv_file = tempfile.NamedTemporaryFile(
                delete=False, mode="w", suffix=".csv"
            )
            self.csv_files.append(csv_file)
            dataframe = pandas.DataFrame(self.data, columns=self.header)
            dataframe.to_csv(csv_file, index=False)
            csv_file.close()

    def tearDown(self):
        for csv_file in self.csv_files:
            os.remove(csv_file.name)

    def test_merge_csv(self):
        merged_dataframe = process_report.merge_csv(
            [csv_file.name for csv_file in self.csv_files]
        )

        expected_rows = len(self.data) * 3
        self.assertEqual(
            len(merged_dataframe), expected_rows
        )  # `len` for a pandas dataframe excludes the header row

        # Assert that the headers in the merged DataFrame match the expected headers
        self.assertListEqual(merged_dataframe.columns.tolist(), self.header)


class TestExportPICSV(TestCase):
    def setUp(self):
        data = {
            "Invoice Month": ["2023-01", "2023-01", "2023-01", "2023-01", "2023-01"],
            "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
            "Institution": ["BU", "BU", "BU", "HU", "HU"],
            "Project - Allocation": [
                "ProjectA",
                "ProjectB",
                "ProjectC",
                "ProjectD",
                "ProjectE",
            ],
            "Untouch Data Column": ["DataA", "DataB", "DataC", "DataD", "DataE"],
            "Is Billable": [True, True, True, True, True],
            "Missing PI": [False, False, False, False, False],
        }
        self.dataframe = pandas.DataFrame(data)
        self.invoice_month = data["Invoice Month"][0]

    @mock.patch("process_report.invoices.invoice.Invoice._filter_columns")
    def test_export_pi(self, mock_filter_cols):
        mock_filter_cols.return_value = self.dataframe

        output_dir = tempfile.TemporaryDirectory()
        pi_inv = test_utils.new_pi_specific_invoice(
            output_dir.name, invoice_month=self.invoice_month, data=self.dataframe
        )
        pi_inv.process()
        pi_inv.export()
        pi_csv_1 = f'{self.dataframe["Institution"][0]}_{self.dataframe["Manager (PI)"][0]} {self.dataframe["Invoice Month"][0]}.csv'
        pi_csv_2 = f'{self.dataframe["Institution"][3]}_{self.dataframe["Manager (PI)"][3]} {self.dataframe["Invoice Month"][3]}.csv'
        self.assertIn(pi_csv_1, os.listdir(output_dir.name))
        self.assertIn(pi_csv_2, os.listdir(output_dir.name))
        self.assertEqual(
            len(os.listdir(output_dir.name)),
            len(self.dataframe["Manager (PI)"].unique()),
        )

        pi_df = pandas.read_csv(output_dir.name + "/" + pi_csv_1)
        self.assertEqual(len(pi_df["Manager (PI)"].unique()), 1)
        self.assertEqual(
            pi_df["Manager (PI)"].unique()[0], self.dataframe["Manager (PI)"][0]
        )

        self.assertIn("ProjectA", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectB", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectC", pi_df["Project - Allocation"].tolist())

        pi_df = pandas.read_csv(output_dir.name + "/" + pi_csv_2)
        self.assertEqual(len(pi_df["Manager (PI)"].unique()), 1)
        self.assertEqual(
            pi_df["Manager (PI)"].unique()[0], self.dataframe["Manager (PI)"][3]
        )

        self.assertIn("ProjectD", pi_df["Project - Allocation"].tolist())
        self.assertIn("ProjectE", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectA", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectB", pi_df["Project - Allocation"].tolist())
        self.assertNotIn("ProjectC", pi_df["Project - Allocation"].tolist())


class TestAddInstituteProcessor(TestCase):
    def test_get_pi_institution(self):
        institute_map = {
            "harvard.edu": "Harvard University",
            "bu.edu": "Boston University",
            "bentley.edu": "Bentley",
            "mclean.harvard.edu": "McLean Hospital",
            "northeastern.edu": "Northeastern University",
            "childrens.harvard.edu": "Boston Children's Hospital",
            "meei.harvard.edu": "Massachusetts Eye & Ear",
            "dfci.harvard.edu": "Dana-Farber Cancer Institute",
            "bwh.harvard.edu": "Brigham and Women's Hospital",
            "bidmc.harvard.edu": "Beth Israel Deaconess Medical Center",
        }

        answers = {
            "q@bu.edu": "Boston University",
            "c@mclean.harvard.edu": "McLean Hospital",
            "b@harvard.edu": "Harvard University",
            "e@edu": "",
            "pi@northeastern.edu": "Northeastern University",
            "h@a.b.c.harvard.edu": "Harvard University",
            "c@a.childrens.harvard.edu": "Boston Children's Hospital",
            "d@a-b.meei.harvard.edu": "Massachusetts Eye & Ear",
            "e@dfci.harvard": "",
            "f@bwh.harvard.edu": "Brigham and Women's Hospital",
            "g@bidmc.harvard.edu": "Beth Israel Deaconess Medical Center",
        }

        add_institute_proc = test_utils.new_add_institution_processor()

        for pi_email, answer in answers.items():
            self.assertEqual(
                add_institute_proc._get_institution_from_pi(institute_map, pi_email),
                answer,
            )


class TestValidateAliasProcessor(TestCase):
    def test_validate_alias(self):
        alias_map = {"PI1": ["PI1_1", "PI1_2"], "PI2": ["PI2_1"]}
        test_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", "PI1_1", "PI1_2", "PI2_1", "PI2_1"],
            }
        )
        answer_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", "PI1", "PI1", "PI2", "PI2"],
            }
        )

        validate_pi_alias_proc = test_utils.new_validate_pi_alias_processor(
            data=test_data, alias_map=alias_map
        )
        validate_pi_alias_proc.process()
        self.assertTrue(answer_data.equals(validate_pi_alias_proc.data))


class TestValidateBillablePIProcessor(TestCase):
    def test_remove_nonbillables(self):
        pis = [uuid.uuid4().hex for x in range(10)]
        projects = [uuid.uuid4().hex for x in range(10)]
        nonbillable_pis = pis[:3]
        nonbillable_projects = projects[7:]
        billable_pis = pis[3:7]
        data = pandas.DataFrame({"Manager (PI)": pis, "Project - Allocation": projects})

        validate_billable_pi_proc = test_utils.new_validate_billable_pi_processor(
            data=data,
            nonbillable_pis=nonbillable_pis,
            nonbillable_projects=nonbillable_projects,
        )
        validate_billable_pi_proc.process()
        data = validate_billable_pi_proc.data
        data = data[data["Is Billable"]]
        self.assertTrue(data[data["Manager (PI)"].isin(nonbillable_pis)].empty)
        self.assertTrue(
            data[data["Project - Allocation"].isin(nonbillable_projects)].empty
        )
        self.assertTrue(data["Manager (PI)"].isin(billable_pis).all())

    def test_empty_pi_name(self):
        test_data = pandas.DataFrame(
            {
                "Manager (PI)": ["PI1", math.nan, "PI1", "PI2", "PI2"],
                "Project - Allocation": [
                    "ProjectA",
                    "ProjectB",
                    "ProjectC",
                    "ProjectD",
                    "ProjectE",
                ],
            }
        )
        self.assertEqual(1, len(test_data[pandas.isna(test_data["Manager (PI)"])]))
        validate_billable_pi_proc = test_utils.new_validate_billable_pi_processor(
            data=test_data
        )
        validate_billable_pi_proc.process()
        output_data = validate_billable_pi_proc.data
        output_data = output_data[~output_data["Missing PI"]]
        self.assertEqual(0, len(output_data[pandas.isna(output_data["Manager (PI)"])]))


class TestMonthUtils(TestCase):
    def test_get_month_diff(self):
        testcases = [
            (("2024-12", "2024-03"), 9),
            (("2024-12", "2023-03"), 21),
            (("2024-11", "2024-12"), -1),
            (("2024-12", "2025-03"), -3),
        ]
        for arglist, answer in testcases:
            self.assertEqual(util.get_month_diff(*arglist), answer)
        with self.assertRaises(ValueError):
            util.get_month_diff("2024-16", "2025-03")


class TestNewPICreditProcessor(TestCase):
    def _assert_result_invoice_and_old_pi_file(
        self,
        invoice_month,
        test_invoice,
        test_old_pi_filepath,
        answer_invoice,
        answer_old_pi_df,
    ):
        new_pi_credit_proc = test_utils.new_new_pi_credit_processor(
            invoice_month=invoice_month,
            data=test_invoice,
            old_pi_filepath=test_old_pi_filepath,
        )
        new_pi_credit_proc.process()
        output_invoice = new_pi_credit_proc.data
        output_old_pi_df = new_pi_credit_proc.updated_old_pi_df.sort_values(
            by="PI", ignore_index=True
        )

        answer_invoice = answer_invoice.astype(output_invoice.dtypes)
        answer_old_pi_df = answer_old_pi_df.astype(output_old_pi_df.dtypes).sort_values(
            by="PI", ignore_index=True
        )

        self.assertTrue(output_invoice.equals(answer_invoice))
        self.assertTrue(output_old_pi_df.equals(answer_old_pi_df))

    def _get_test_invoice(
        self, pi, cost, su_type=None, is_billable=None, missing_pi=None
    ):
        if not su_type:
            su_type = ["CPU" for _ in range(len(pi))]

        if not is_billable:
            is_billable = [True for _ in range(len(pi))]

        if not missing_pi:
            missing_pi = [False for _ in range(len(pi))]

        return pandas.DataFrame(
            {
                "Manager (PI)": pi,
                "Cost": cost,
                "SU Type": su_type,
                "Is Billable": is_billable,
                "Missing PI": missing_pi,
            }
        )

    def setUp(self) -> None:
        self.test_old_pi_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", suffix=".csv"
        )

    def tearDown(self) -> None:
        os.remove(self.test_old_pi_file.name)

    def test_no_new_pi(self):
        test_invoice = self._get_test_invoice(
            ["PI" for _ in range(3)], [100 for _ in range(3)]
        )

        # Other fields of old PI file not accessed if PI is no longer
        # eligible for new-PI credit
        test_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-01"],
                "Initial Credits": [1000],
            }
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [None for _ in range(3)],
                        "Credit Code": [None for _ in range(3)],
                        "PI Balance": [100 for _ in range(3)],
                        "Balance": [100 for _ in range(3)],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = test_old_pi_df.copy()

        self._assert_result_invoice_and_old_pi_file(
            "2024-06",
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_one_new_pi(self):
        """Invoice with one completely new PI"""

        # One allocation
        invoice_month = "2024-06"

        test_invoice = self._get_test_invoice(["PI"], [100])

        test_old_pi_df = pandas.DataFrame(
            columns=[
                "PI",
                "First Invoice Month",
                "Initial Credits",
                "1st Month Used",
                "2nd Month Used",
            ]
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [100],
                        "Credit Code": ["0002"],
                        "PI Balance": [0],
                        "Balance": [0],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [100],
                "2nd Month Used": [0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

        # Two allocations, costs partially covered
        test_invoice = self._get_test_invoice(["PI", "PI"], [500, 1000])

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [500, 500],
                        "Credit Code": ["0002", "0002"],
                        "PI Balance": [0, 500],
                        "Balance": [0, 500],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [1000],
                "2nd Month Used": [0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

        # Two allocations, costs completely covered
        test_invoice = self._get_test_invoice(["PI", "PI"], [500, 400])

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [500, 400],
                        "Credit Code": ["0002", "0002"],
                        "PI Balance": [0, 0],
                        "Balance": [0, 0],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [900],
                "2nd Month Used": [0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_one_month_pi(self):
        """PI has appeared in invoices for one month"""

        # Remaining credits completely covers costs
        invoice_month = "2024-07"
        test_invoice = self._get_test_invoice(["PI"], [200])

        test_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [500],
                "2nd Month Used": [0],
            }
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [200],
                        "Credit Code": ["0002"],
                        "PI Balance": [0],
                        "Balance": [0],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [500],
                "2nd Month Used": [200],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

        # Remaining credits partially covers costs
        test_invoice = self._get_test_invoice(["PI"], [600])

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [500],
                        "Credit Code": ["0002"],
                        "PI Balance": [100],
                        "Balance": [100],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [500],
                "2nd Month Used": [500],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_two_new_pi(self):
        """Two PIs of different age"""

        # Costs partially and completely covered
        invoice_month = "2024-07"
        test_invoice = self._get_test_invoice(["PI1", "PI1", "PI2"], [800, 500, 500])

        test_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI1"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [500],
                "2nd Month Used": [0],
            }
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [500, None, 500],
                        "Credit Code": ["0002", None, "0002"],
                        "PI Balance": [300, 500, 0],
                        "Balance": [300, 500, 0],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI1", "PI2"],
                "First Invoice Month": ["2024-06", "2024-07"],
                "Initial Credits": [1000, 1000],
                "1st Month Used": [500, 500],
                "2nd Month Used": [500, 0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_old_pi_file_overwritten(self):
        """If PI already has entry in Old PI file,
        their initial credits and PI entry could be overwritten"""

        invoice_month = "2024-06"
        test_invoice = self._get_test_invoice(["PI", "PI"], [500, 500])
        test_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [500],
                "1st Month Used": [200],
                "2nd Month Used": [0],
            }
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [500, None],
                        "Credit Code": ["0002", None],
                        "PI Balance": [0, 500],
                        "Balance": [0, 500],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [500],
                "1st Month Used": [500],
                "2nd Month Used": [0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_excluded_su_types(self):
        """Certain SU types can be excluded from the credit"""

        invoice_month = "2024-06"
        test_invoice = self._get_test_invoice(
            ["PI", "PI", "PI", "PI"],
            [600, 600, 600, 600],
            [
                "CPU",
                "OpenShift GPUA100SXM4",
                "GPU",
                "OpenStack GPUA100SXM4",
            ],
        )

        test_old_pi_df = pandas.DataFrame(
            columns=[
                "PI",
                "First Invoice Month",
                "Initial Credits",
                "1st Month Used",
                "2nd Month Used",
            ]
        )
        test_old_pi_df.to_csv(self.test_old_pi_file.name, index=False)

        answer_invoice = pandas.concat(
            [
                test_invoice,
                pandas.DataFrame(
                    {
                        "Credit": [600, None, 400, None],
                        "Credit Code": ["0002", None, "0002", None],
                        "PI Balance": [0, 600, 200, 600],
                        "Balance": [0, 600, 200, 600],
                    }
                ),
            ],
            axis=1,
        )

        answer_old_pi_df = pandas.DataFrame(
            {
                "PI": ["PI"],
                "First Invoice Month": ["2024-06"],
                "Initial Credits": [1000],
                "1st Month Used": [1000],
                "2nd Month Used": [0],
            }
        )

        self._assert_result_invoice_and_old_pi_file(
            invoice_month,
            test_invoice,
            self.test_old_pi_file.name,
            answer_invoice,
            answer_old_pi_df,
        )

    def test_apply_credit_error(self):
        """Test faulty data"""
        old_pi_df = pandas.DataFrame(
            {"PI": ["PI1"], "First Invoice Month": ["2024-04"]}
        )
        invoice_month = "2024-03"
        test_invoice = test_utils.new_new_pi_credit_processor()
        with self.assertRaises(SystemExit):
            test_invoice._get_pi_age(old_pi_df, "PI1", invoice_month)


class TestBUSubsidyProcessor(TestCase):
    def _assert_result_invoice(
        self,
        subsidy_amount,
        test_invoice,
        answer_invoice,
        invoice_month="0000-00",
    ):
        new_bu_subsidy_proc = test_utils.new_bu_subsidy_processor(
            invoice_month=invoice_month,
            data=test_invoice,
            subsidy_amount=subsidy_amount,
        )
        new_bu_subsidy_proc.process()
        output_invoice = new_bu_subsidy_proc.data
        answer_invoice = answer_invoice.astype(output_invoice.dtypes)
        print(output_invoice)
        print(answer_invoice)

        self.assertTrue(output_invoice.equals(answer_invoice))

    def _get_test_invoice(
        self,
        pi,
        pi_balances,
        balances=None,
        project_names=None,
        institution=None,
        is_billable=None,
        missing_pi=None,
    ):
        if not balances:
            balances = pi_balances

        if not project_names:
            project_names = ["Project" for _ in range(len(pi))]

        if not institution:
            institution = ["Boston University" for _ in range(len(pi))]

        if not is_billable:
            is_billable = [True for _ in range(len(pi))]

        if not missing_pi:
            missing_pi = [False for _ in range(len(pi))]

        return pandas.DataFrame(
            {
                "Manager (PI)": pi,
                "Project - Allocation": project_names,
                "PI Balance": pi_balances,
                "Balance": balances,
                "Institution": institution,
                "Is Billable": is_billable,
                "Missing PI": missing_pi,
            }
        )

    def test_exclude_non_BU_pi(self):
        """Are only BU PIs given the subsidy?"""

        subsidy_amount = 100
        test_invoice = self._get_test_invoice(
            [str(i) for i in range(5)],
            pi_balances=[subsidy_amount for _ in range(5)],
            institution=[
                "Boston University",
                "Boston University",
                "boston university",
                "Harvard University",
                "BU",
            ],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = answer_invoice["Project - Allocation"]
        answer_invoice["Subsidy"] = [subsidy_amount, subsidy_amount, 0, 0, 0]
        answer_invoice["PI Balance"] = [
            0,
            0,
            subsidy_amount,
            subsidy_amount,
            subsidy_amount,
        ]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)

    def test_exclude_nonbillables(self):
        """Are nonbillables excluded from the subsidy?"""
        subsidy_amount = 100
        test_invoice = self._get_test_invoice(
            [str(i) for i in range(6)],
            pi_balances=[subsidy_amount for _ in range(6)],
            is_billable=[True, True, False, False, True, True],
            missing_pi=[True, True, False, False, False, False],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = answer_invoice["Project - Allocation"]
        answer_invoice["Subsidy"] = [0, 0, 0, 0, subsidy_amount, subsidy_amount]
        answer_invoice["PI Balance"] = [
            subsidy_amount,
            subsidy_amount,
            subsidy_amount,
            subsidy_amount,
            0,
            0,
        ]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)

    def test_one_pi_many_allocations(self):
        """Is subsidy applied properly to BU PI with many allocations?"""

        # Two projects, one allocation each
        subsidy_amount = 100
        test_invoice = self._get_test_invoice(
            ["PI" for i in range(2)],
            pi_balances=[60, 60],
            project_names=["P1", "P2"],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = answer_invoice["Project - Allocation"]
        answer_invoice["Subsidy"] = [60, 40]
        answer_invoice["PI Balance"] = [0, 20]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)

        # Two projects, two allocations each
        test_invoice = self._get_test_invoice(
            ["PI" for i in range(4)],
            pi_balances=[40, 40, 40, 40],
            project_names=["P1-A1", "P1-A1-test", "P2", "P2-"],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = ["P1", "P1-A1", "P2", "P2"]
        answer_invoice["Subsidy"] = [40, 40, 20, 0]
        answer_invoice["PI Balance"] = [0, 0, 20, 40]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)

        # Two allocations, one where PI balance != NERC balance
        test_invoice = self._get_test_invoice(
            ["PI" for i in range(2)],
            pi_balances=[80, 80],
            project_names=["P1", "P2"],
            balances=[100, 80],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = answer_invoice["Project - Allocation"]
        answer_invoice["Subsidy"] = [80, 20]
        answer_invoice["PI Balance"] = [0, 60]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)

    def test_two_pi(self):
        """Is subsidy applied to more than one PI?"""
        # Each PI has two allocations
        subsidy_amount = 100
        test_invoice = self._get_test_invoice(
            ["PI1", "PI1", "PI2", "PI2"],
            pi_balances=[80, 80, 40, 40],
        )

        answer_invoice = test_invoice.copy()
        answer_invoice["Project"] = answer_invoice["Project - Allocation"]
        answer_invoice["Subsidy"] = [80, 20, 40, 40]
        answer_invoice["PI Balance"] = [0, 60, 0, 0]

        self._assert_result_invoice(subsidy_amount, test_invoice, answer_invoice)


class TestLenovoProcessor(TestCase):
    def test_process_lenovo(self):
        test_invoice = pandas.DataFrame(
            {
                "SU Hours (GBhr or SUhr)": [1, 10, 100, 4, 432, 10],
            }
        )
        answer_invoice = test_invoice.copy()
        answer_invoice["SU Charge"] = 1
        answer_invoice["Charge"] = (
            answer_invoice["SU Hours (GBhr or SUhr)"] * answer_invoice["SU Charge"]
        )

        lenovo_proc = test_utils.new_lenovo_processor(data=test_invoice)
        lenovo_proc.process()
        self.assertTrue(lenovo_proc.data.equals(answer_invoice))


class TestUploadToS3(TestCase):
    @mock.patch("process_report.util.get_invoice_bucket")
    @mock.patch("process_report.util.get_iso8601_time")
    def test_upload_to_s3(self, mock_get_time, mock_get_bucket):
        mock_bucket = mock.MagicMock()
        mock_get_bucket.return_value = mock_bucket
        mock_get_time.return_value = "0"

        invoice_month = "2024-03"
        filenames = ["test-test", "test2.test", "test3"]
        sample_base_invoice = test_utils.new_base_invoice(invoice_month=invoice_month)

        answers = [
            (
                f"test-test {invoice_month}.csv",
                f"Invoices/{invoice_month}/test-test {invoice_month}.csv",
            ),
            (
                f"test-test {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test-test {invoice_month} 0.csv",
            ),
            (
                f"test2.test {invoice_month}.csv",
                f"Invoices/{invoice_month}/test2.test {invoice_month}.csv",
            ),
            (
                f"test2.test {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test2.test {invoice_month} 0.csv",
            ),
            (
                f"test3 {invoice_month}.csv",
                f"Invoices/{invoice_month}/test3 {invoice_month}.csv",
            ),
            (
                f"test3 {invoice_month}.csv",
                f"Invoices/{invoice_month}/Archive/test3 {invoice_month} 0.csv",
            ),
        ]

        for filename in filenames:
            sample_base_invoice.name = filename
            sample_base_invoice.export_s3(mock_bucket)

        for i, call_args in enumerate(mock_bucket.upload_file.call_args_list):
            self.assertTrue(answers[i] in call_args)


class TestNERCRates(TestCase):
    @mock.patch("process_report.util.load_institute_list")
    def test_flag_limit_new_pi_credit(self, mock_load_institute_list):
        mock_load_institute_list.return_value = [
            {"display_name": "BU", "mghpcc_partnership_start_date": "2024-02"},
            {"display_name": "HU", "mghpcc_partnership_start_date": "2024-6"},
            {"display_name": "NEU", "mghpcc_partnership_start_date": "2024-11"},
        ]
        sample_df = pandas.DataFrame(
            {
                "Institution": ["BU", "HU", "NEU", "MIT", "BC"],
            }
        )
        sample_proc = test_utils.new_new_pi_credit_processor(
            limit_new_pi_credit_to_partners=True
        )

        # When no partnerships are active
        sample_proc.invoice_month = "2024-01"
        output_df = sample_proc._filter_partners(sample_df)
        self.assertTrue(output_df.empty)

        # When some partnerships are active
        sample_proc.invoice_month = "2024-06"
        output_df = sample_proc._filter_partners(sample_df)
        answer_df = pandas.DataFrame({"Institution": ["BU", "HU"]})
        self.assertTrue(output_df.equals(answer_df))

        # When all partnerships are active
        sample_proc.invoice_month = "2024-12"
        output_df = sample_proc._filter_partners(sample_df)
        answer_df = pandas.DataFrame({"Institution": ["BU", "HU", "NEU"]})
        self.assertTrue(output_df.equals(answer_df))


class TestBaseInvoice(TestCase):
    def test_filter_exported_columns(self):
        test_invoice = pandas.DataFrame(columns=["C1", "C2", "C3", "C4", "C5"])
        answer_invoice = pandas.DataFrame(columns=["C1", "C3R", "C5R"])
        inv = test_utils.new_base_invoice()
        inv.export_data = test_invoice
        inv.export_columns_list = ["C1", "C3", "C5"]
        inv.exported_columns_map = {"C3": "C3R", "C5": "C5R"}

        inv._filter_columns()
        result_invoice = inv.export_data
        self.assertTrue(result_invoice.equals(answer_invoice))
