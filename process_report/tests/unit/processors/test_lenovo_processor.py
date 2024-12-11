from unittest import TestCase
import pandas

from process_report.tests import util as test_utils


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
