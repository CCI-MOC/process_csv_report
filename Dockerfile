FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git chromium

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY tools/ tools/
COPY process_report/process_report.py process_report/
COPY process_report/institute_list.yaml process_report/

CMD ["tools/clone_nonbillables_and_process_invoice.sh"]
