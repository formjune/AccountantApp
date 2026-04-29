import os
import matplotlib
import collections




# from sql.Tables import *
from sql.EngineSQL import *
from sql.Enumerators import *



def findTransferAmount():
    pass


def main():
    transfers = Cache.get(Transfers)
    staff = Cache.get(Staff, where=lambda s: s.type != StaffTypeEnum.dismissed)
    tags = {t.id: t.name for t in Cache.get(Tags)}

    for user in staff:
        amount = 0
        months = collections.defaultdict(float)
        wallet = user.wallet.lower()
        for tx in transfers:
            if tx.receier.lower() != wallet:
                continue
            amount += tx.amount_tx
            months[(tx.date.year, tx.date.month)] += tx.amount_tx
        print(amount)
        print(months)


main()
