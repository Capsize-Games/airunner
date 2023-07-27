from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from airunner.database.controllers.app_controller import AppController
from airunner.database.controllers.generator_controller import GeneratorController
from airunner.database.controllers.grid_controller import GridController
from airunner.database.controllers.image_export_controller import ImageExportController
from airunner.database.controllers.memory_controller import MemoryController
from airunner.database.controllers.path_controller import PathController
from airunner.database.controllers.prompt_builder_controller import PromptBuilderController
from airunner.database.controllers.tool_controller import ToolController


class DatabaseController:
    _engine = None
    _session = None
    db_name = ""

    @property
    def engine(self):
        if not self._engine:
            self._engine = create_engine(f"sqlite:///{self.db_name}.db")
        return self._engine

    @property
    def session(self):
        if not self._session:
            self._session = Session = sessionmaker(bind=self.engine)
            self._session = Session()
        return self._session

    def __init__(self, db_name="airunner"):
        self.db_name = db_name
        self.app_settings = AppController(engine=self.engine, session=self.session)
        self.generator_settings = GeneratorController(engine=self.engine, session=self.session)
        self.create_all()

    def save(self):
        self.session.commit()

    def create_all(self):
        for controller in [
            self.app_settings,
            self.generator_settings
        ]:
            if controller.model_class:
                controller.model_class.metadata.create_all(self.engine)
