import collections
import datetime
import os.path
from idlelib.iomenu import encoding

from sql.EngineSQL import *
from blockchain.EngineWeb3 import *


date_start = datetime.date(year=2000, month=1, day=1)
date_end = datetime.date(year=2050, month=12, day=31)
output_file = "result_months.csv"


# do not edit


class FileWriter(object):

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self.file = open(self.filename, "w", encoding="utf-8")
        return self

    def __exit__(self, *args):
        self.file.close()

    def write(self, message=""):
        if os.path.isdir("C:/users/andrey"):
            print(message)
        else:
            self.file.write(message + "\n")


result = collections.defaultdict(list)


with Session() as session:

    all_staff = {s.id: s for s in session.query(Staff).all()}
    all_staff = {s.wallet.lower(): all_staff[s.staff] for s in session.query(StaffWallets).all()}
    spending = {s.transaction.lower().split("/")[-1]: s.comment for s in session.query(Spending).all()}

    for tx in session.query(Transfers).all():

        receiver = tx.receiver.lower()
        if receiver not in all_staff:
            continue
        receiver = all_staff[receiver]
        receiver = receiver.name

        tx_date = tx.date.date()
        if not date_start <= tx_date <= date_end:
            continue
        tx_date = datetime.datetime(year=tx_date.year, month=tx_date.month, day=1)

        url = getUrl(tx.tx_hash, tx.network)
        amount = str(tx.amount_tx)
        if tx.tx_hash in spending:
            comment = spending[tx.tx_hash]
        else:
            comment = ""
        result[tx_date].append([receiver, amount, url, comment])


with FileWriter(output_file) as file:
    file.write("staff,amount,url,comment")
    for tag in sorted(result):
        block = result[tag]
        file.write(tag.strftime('%Y %B'))
        for line in block:
            file.write(",".join(line))
        file.write()
