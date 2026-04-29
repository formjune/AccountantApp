import json
import os.path


config = {
    "formatter": True,
    "timeout": 15,
    "bd_ping": 30,
    "pool_size": 10,
    "max_overflow": 20
}
if os.path.isfile("config.json"):
    config.update(json.load(open("config.json")))
else:
    config.update(json.load(open("resources/dev_config.json")))
USERNAME = config["username"]
PASSWORD = config["password"]
HOST = config["host"]
PORT = config["port"]
DATABASE = config["database"]
API_KEYS = config["apikeys"]
TIMEOUT = config["timeout"]
BD_PING = config["bd_ping"]
POOL_SIZE = config["pool_size"]
MAX_OVERFLOW = config["max_overflow"]
del config
