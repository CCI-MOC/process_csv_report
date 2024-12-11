from unittest import TestCase

from process_report.tests import util as test_utils


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
