from dataclasses import dataclass

import pandas

from process_report.invoices import invoice
from process_report.processors import processor
from process_report import util


@dataclass
class AddInstitutionProcessor(processor.Processor):
    def _add_institution(self):
        """Determine every PI's institution name, logging any PI whose institution cannot be determined
        This is performed by `get_institution_from_pi()`, which tries to match the PI's username to
        a list of known institution email domains (i.e bu.edu), or to several edge cases (i.e rudolph) if
        the username is not an email address.

        Exact matches are then mapped to the corresponding institution name.

        I.e "foo@bu.edu" would match with "bu.edu", which maps to the instition name "Boston University"

        The list of mappings are defined in `institute_map.json`.
        """
        institute_list = util.load_institute_list()
        institute_map = util.get_institute_mapping(institute_list)
        self.data = self.data.astype({invoice.INSTITUTION_FIELD: "str"})
        for i, row in self.data.iterrows():
            pi_name = row[invoice.PI_FIELD]
            if pandas.isna(pi_name):
                print(f"Project {row[invoice.PROJECT_FIELD]} has no PI")
            else:
                self.data.at[
                    i, invoice.INSTITUTION_FIELD
                ] = util.get_institution_from_pi(institute_map, pi_name)

    def _process(self):
        self._add_institution()
