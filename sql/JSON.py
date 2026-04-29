import json
from sql.EngineSQL import *
from sql.Tables import *
from sql.Convert import *
import sql.Tables as Tables


all_tables = []


def toJson(filename: str = "db.json"):
    data = {table.__tablename__: [asDict(data) for data in loadTable(table)] for table in all_tables}
    json.dump(data, open(filename, "w", encoding="utf-8"), indent=2)


def fromJson(filename: str = "db.json"):
    table_data = json.load(open(filename, encoding="utf-8"))
    for table in reversed(all_tables):
        table.__table__.drop(engine)
    Base.metadata.create_all(engine)
    EngineSQL.startTask()
    
    for table in all_tables:
        try:
            items = [asItem(table, item) for item in table_data[table.__tablename__]]
        except KeyError:
            continue
        if not items:
            continue
        items = {item.id: item for item in items}
        max_id = max(items)
        with Session() as session:
            for index in range(max_id):
                session.add(table())
            session.commit()
            empty_items = session.query(table).all()
            for empty_item in empty_items:
                try:
                    update(empty_item, items[empty_item.id])
                except KeyError:
                    session.delete(empty_item)
            session.commit()


def loadTables():
    for table in Tables.__all__:
        table = Tables.__getattribute__(table)
        if hasattr(table, "slots"):
            all_tables.append(table)


loadTables()
