"""Development-mode preset — single-user SQLite, debug on."""

DEPLOYMENT_MODE = "development"
DEBUG = True
DATABASE_BACKEND = "sqlite"
SQLITE_DB_NAME = "airunner.dev.db"
AIRUNNER_SERVER_HOST = "localhost"
AIRUNNER_SERVER_PORT = 8080
AIRUNNER_INSECURE_NO_AUTH = "1"
