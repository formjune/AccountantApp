import datetime
import json


data = json.load(open(r"db.json"))

spendings = data["spending"]
regular_spendings = data["regular_spending"]
start_date = datetime.date(2024, 11, 1)
end_date = datetime.date(2024, 11, 30)

def get_spending_name(id, type):
    for spending in regular_spendings:
        if spending["id"] == id and type == "regular":
            return spending["purpose"]
    return "Unknown"


with open("projected_monthly_expenses.csv", "w", encoding="utf-8") as file:
    file.write("Spending,Amount\n")
    for spending in spendings:
        date = datetime.datetime.strptime(spending["date"], "%Y-%m-%d").date()
        if start_date <= date <= end_date and spending["status"] == "unpaid":
            file.write(f"{get_spending_name(spending['spending_id'], spending['spending_type'])},{spending['amount']}\n")
