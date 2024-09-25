from dataclasses import dataclass

import pandas

from process_report.invoices import invoice
from process_report.processors import processor


@dataclass
class ValidatePIAliasProcessor(processor.Processor):
    alias_map: dict

    @staticmethod
    def _validate_pi_aliases(dataframe: pandas.DataFrame, alias_dict: dict):
        for pi, pi_aliases in alias_dict.items():
            dataframe.loc[
                dataframe[invoice.PI_FIELD].isin(pi_aliases), invoice.PI_FIELD
            ] = pi

        return dataframe

    def _process(self):
        self.data = self._validate_pi_aliases(self.data, self.alias_map)
