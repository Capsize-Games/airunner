import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from airunner.data.models.settings_models import Base

class DatabaseHandler:
    def __init__(self, db_path=os.path.expanduser(
        os.path.join(
            "~",
            ".local",
            "share",
            "airunner",
            "data",
            "airunner.db"
        )
    )):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.conversation_id = None

    def get_db_session(self):
        return self.Session()
