import os
from datetime import timedelta


class DefaultConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(DefaultConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False


def _make_cloud_sql_creator():
    """Return a SQLAlchemy creator callable using Cloud SQL Python Connector."""
    from google.cloud.sql.connector import Connector

    instance = os.environ.get("CLOUD_SQL_INSTANCE", "")
    db_name = os.environ.get("DB_NAME", "")
    db_user = os.environ.get("DB_USER", "")
    db_password = os.environ.get("DB_PASSWORD", "")

    connector = Connector()

    def creator():
        connect_kwargs = {
            "instance_connection_name": instance,
            "driver": "pg8000",
            "user": db_user,
            "db": db_name,
        }
        if db_password:
            connect_kwargs["password"] = db_password
        else:
            connect_kwargs["enable_iam_auth"] = True
        return connector.connect(**connect_kwargs)

    return creator


class ProductionConfig(DefaultConfig):
    DEBUG = False
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = "postgresql+pg8000://"

    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self):  # noqa: N802
        if os.environ.get("CLOUD_SQL_INSTANCE"):
            return {"creator": _make_cloud_sql_creator()}
        return {}


config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
