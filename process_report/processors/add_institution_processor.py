from dataclasses import dataclass
import json

import pandas

from process_report.invoices import invoice
from process_report.processors import processor


@dataclass
class AddInstitutionProcessor(processor.Processor):
    @staticmethod
    def _load_institute_map() -> dict:
        with open("process_report/institute_map.json", "r") as f:
            institute_map = json.load(f)

        return institute_map

    @staticmethod
    def _get_institution_from_pi(institute_map, pi_uname):
        institution_domain = pi_uname.split("@")[-1]
        for i in range(institution_domain.count(".") + 1):
            if institution_name := institute_map.get(institution_domain, ""):
                break
            institution_domain = institution_domain[institution_domain.find(".") + 1 :]

        if institution_name == "":
            print(f"Warning: PI name {pi_uname} does not match any institution!")

        return institution_name

    def _add_institution(self, dataframe: pandas.DataFrame):
        """Determine every PI's institution name, logging any PI whose institution cannot be determined
        This is performed by `get_institution_from_pi()`, which tries to match the PI's username to
        a list of known institution email domains (i.e bu.edu), or to several edge cases (i.e rudolph) if
        the username is not an email address.

        Exact matches are then mapped to the corresponding institution name.

        I.e "foo@bu.edu" would match with "bu.edu", which maps to the instition name "Boston University"

        The list of mappings are defined in `institute_map.json`.
        """
        institute_map = self._load_institute_map()
        dataframe = dataframe.astype({invoice.INSTITUTION_FIELD: "str"})
        for i, row in dataframe.iterrows():
            pi_name = row[invoice.PI_FIELD]
            if pandas.isna(pi_name):
                print(f"Project {row[invoice.PROJECT_FIELD]} has no PI")
            else:
                dataframe.at[
                    i, invoice.INSTITUTION_FIELD
                ] = self._get_institution_from_pi(institute_map, pi_name)

        return dataframe

    def _process(self):
        self.data = self._add_institution(self.data)
