import os

BASE_PATH = os.path.join(os.path.expanduser("~"), ".airunner")
SQLITE_DB_NAME = "airunner.db"
SQLITE_DB_PATH = os.path.join(BASE_PATH, SQLITE_DB_NAME)
