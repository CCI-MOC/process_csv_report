from unittest import TestCase, mock
import pandas

from process_report.tests import util as test_utils


class TestBaseInvoice(TestCase):
    def test_filter_exported_columns(self):
        test_invoice = pandas.DataFrame(columns=["C1", "C2", "C3", "C4", "C5"])
        answer_invoice = pandas.DataFrame(columns=["C1", "C3R", "C5R"])
        inv = test_utils.new_base_invoice(data=test_invoice)
        inv.export_columns_list = ["C1", "C3", "C5"]
        inv.exported_columns_map = {"C3": "C3R", "C5": "C5R"}
        result_invoice = inv._filter_columns()

        self.assertTrue(result_invoice.equals(answer_invoice))


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
