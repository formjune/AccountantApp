import datetime
import enum
from sqlalchemy import Boolean, Integer, Float, String, DateTime, Enum
from sql import EngineSQL, Tables


def fromInteger(value: int):
    if value is None:
        return ""
    return str(value)


def fromFloat(value: float) -> str:
    if value is None:
        return ""
    return str(value)


def fromEnumerator(value: enum.Enum) -> str:
    return value.name


def fromBoolean(value: bool) -> str:
    return "true" if value else "false"


def fromDate(value: datetime.date) -> str:
    if value is None:
        return ""
    elif isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d")


def asItem(table, data):
    if isinstance(data, dict):
        data = [data[k.name] for k in table.slots]
    data_dict = {}
    for value, slot, slot_type in zip(data, table.slots, table.types):
        if slot_type == String:
            data_dict[slot.name] = value
        elif slot_type == DateTime:
            data_dict[slot.name] = value
        elif slot_type == Boolean:
            data_dict[slot.name] = value == "true"
        elif slot_type == Integer:
            data_dict[slot.name] = int(value)
        elif slot_type == Float:
            data_dict[slot.name] = float(value)
        elif slot_type == Enum:
            data_dict[slot.name] = table.enums[slot][value]
    return table(**data_dict)


def asTuple(table) -> list:
    result = []
    for slot, data_type in zip(table.slots, table.types):
        value = table.__getattribute__(slot.name)
        if data_type == String:
            result.append(value)
        elif data_type == Boolean:
            result.append(fromBoolean(value))
        elif data_type == Integer:
            result.append(fromInteger(value))
        elif data_type == Float:
            result.append(fromFloat(value))
        elif data_type == Enum:
            result.append(fromEnumerator(value))
        elif data_type == DateTime:
            result.append(fromDate(value))
        else:
            raise UnicodeError(f"not supported format: {data_type}")
    return result


def asDict(table) -> dict:
    result = {}
    for slot, data_type in zip(table.slots, table.types):
        value = table.__getattribute__(slot.name)
        if data_type == String:
            result[slot.name] = value
        elif data_type == Boolean:
            result[slot.name] = fromBoolean(value)
        elif data_type == Integer:
            result[slot.name] = fromInteger(value)
        elif data_type == Float:
            result[slot.name] = fromFloat(value)
        elif data_type == Enum:
            result[slot.name] = fromEnumerator(value)
        elif data_type == DateTime:
            result[slot.name] = fromDate(value)
        else:
            raise UnicodeError(f"not supported format: {data_type}")
    return result


def asTupleView(table) -> list:
    result = []
    for slot, data_type in zip(table.slots_view, table.types_view):
        value = table.__getattribute__(slot.name)
        if data_type == String:
            result.append(value)
        elif data_type == Boolean:
            result.append(fromBoolean(value))
        elif data_type == Integer:
            result.append(fromInteger(value))
        elif data_type == Float:
            result.append(fromFloat(value))
        elif data_type == Enum:
            result.append(fromEnumerator(value))
        elif data_type == DateTime:
            result.append(fromDate(value))
        else:
            raise UnicodeError(f"not supported format: {data_type}")
    return result


def copyItem(table) -> list:
    params = {}
    for item in table.slots:
        params[item.name] = table.__getattribute__(item.name)
    return table.__class__(**params)


def encodeTags(tags_text: str) -> str:
    if not tags_text:
        return ""
    tags_dict = {t.name.lower(): t.id for t in EngineSQL.Cache.get(Tables.Tags, no_cache=True)}
    my_tags = {t.strip() for t in tags_text.lower().split(",") if t.strip()}
    new_tags = my_tags.difference(tags_dict.keys())
    if new_tags:
        EngineSQL.createTags(new_tags)
        tags_dict = {t.name.lower(): t.id for t in EngineSQL.Cache.get(Tables.Tags, no_cache=True)}
    tags_list = ["0"] * max(tags_dict.values())
    for tag in my_tags:
        if tag in tags_dict:
            tags_list[tags_dict[tag] - 1] = "1"
    return "".join(tags_list)


def printItem(table) -> None:
    print({slot.name: table.__getattribute__(slot.name) for slot in table.slots})
