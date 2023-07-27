class BaseController:
    model_class = None

    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

    @property
    def settings(self):
        settings = self.session.query(self.model_class).first()
        if settings is None:
            raise ValueError("No GridSettings found in the database.")
        return settings

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self.settings, key, value)
        self.session.commit()
