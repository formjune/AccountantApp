import os
os.chdir("..")
import psycopg2
from tools import Config


connection = psycopg2.connect(
    host=Config.HOST,
    port=Config.PORT,
    dbname=Config.DATABASE,
    user=Config.USERNAME,
    password=Config.PASSWORD
)


with connection.cursor() as cursor:
    cursor.execute("drop table if exists income cascade")
    cursor.execute("drop table if exists income_type cascade")
    cursor.execute("drop table if exists staff cascade")
    cursor.execute("drop table if exists promotion_commission cascade")
    cursor.execute("drop table if exists promotion_source cascade")
    cursor.execute("drop table if exists regular_spending cascade")
    cursor.execute("drop table if exists onetime_spending cascade")
    cursor.execute("drop table if exists spending cascade")
    cursor.execute("drop table if exists personal_spending cascade")
    cursor.execute("drop table if exists budget cascade")
    cursor.execute("drop table if exists tags cascade")
    cursor.execute("drop table if exists transfers cascade")
    cursor.execute("drop table if exists transfer_wallets")
    cursor.execute("drop table if exists off_days_percent")

connection.commit()
