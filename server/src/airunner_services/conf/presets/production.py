"""Production-mode preset — PostgreSQL multi-tenant, debug off."""

DEPLOYMENT_MODE = "production"
DEBUG = False
DATABASE_BACKEND = "postgresql"
DB_TENANCY_MODE = "multi"
AIRUNNER_SERVER_HOST = "0.0.0.0"
AIRUNNER_SERVER_PORT = 8080
AIRUNNER_INSECURE_NO_AUTH = "0"
