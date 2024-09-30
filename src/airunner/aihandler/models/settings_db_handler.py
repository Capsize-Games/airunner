from typing import List

from airunner.aihandler.models.database_handler import DatabaseHandler
from airunner.aihandler.models.settings_models import Chatbot, AIModels, Schedulers, Lora, PathSettings, SavedPrompt, \
    Embedding, PromptTemplate, ControlnetModel, FontSetting, PipelineModel, ShortcutKeys, \
    GeneratorSettings, WindowSettings


class SettingsDBHandler(DatabaseHandler):
    #######################################
    ### SCHEDULERS ###
    #######################################
    def load_schedulers(self) -> List[Schedulers]:
        session = self.get_db_session()
        try:
            return session.query(Schedulers).all()
        finally:
            session.close()

    #######################################
    ### SETTINGS ###
    #######################################
    def load_settings_from_db(self, model_class_):
        session = self.get_db_session()
        try:
            settings = session.query(model_class_).first()
            if settings is None:
                settings = self.create_new_settings(model_class_)
        finally:
            session.close()
        return settings

    def update_setting(self, model_class_, name, value):
        session = self.get_db_session()
        try:
            setting = session.query(model_class_).order_by(model_class_.id.desc()).first()
            if setting:
                setattr(setting, name, value)
                session.commit()
        finally:
            session.close()

    def save_generator_settings(self, generator_settings: GeneratorSettings):
        session = self.get_db_session()
        try:
            query = session.query(GeneratorSettings).filter_by(
                id=generator_settings.id
            ).first()
            if query:
                for key in generator_settings.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(generator_settings, key))
            else:
                session.add(generator_settings)
            session.commit()
        finally:
            session.close()

    def reset_settings(self):
        print("TODO")
        pass

    def create_new_settings(self, model_class_):
        session = self.get_db_session()
        try:
            new_settings = model_class_()
            session.add(new_settings)
            session.commit()
            session.refresh(new_settings)
        finally:
            session.close()
        return new_settings

    #######################################
    ### SAVED PROMPTS ###
    #######################################
    def get_saved_prompt_by_id(self, prompt_id) -> SavedPrompt:
        session = self.get_db_session()
        try:
            return session.query(SavedPrompt).filter_by(id=prompt_id).first()
        finally:
            session.close()

    def update_saved_prompt(self, saved_prompt: SavedPrompt):
        session = self.get_db_session()
        try:
            query = session.query(SavedPrompt).filter_by(
                id=saved_prompt.id
            ).first()
            if query:
                for key in saved_prompt.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(saved_prompt, key))
            else:
                session.add(saved_prompt)
            session.commit()
        finally:
            session.close()

    def create_saved_prompt(self, data: dict):
        session = self.get_db_session()
        try:
            new_saved_prompt = SavedPrompt(**data)
            session.add(new_saved_prompt)
            session.commit()
        finally:
            session.close()

    def load_saved_prompts(self) -> List[SavedPrompt]:
        session = self.get_db_session()
        try:
            return session.query(SavedPrompt).all()
        finally:
            session.close()

    def load_font_settings(self) -> List[FontSetting]:
        session = self.get_db_session()
        try:
            return session.query(FontSetting).all()
        finally:
            session.close()

    def get_font_setting_by_name(self, name) -> FontSetting:
        session = self.get_db_session()
        try:
            return session.query(FontSetting).filter_by(name=name).first()
        finally:
            session.close()

    def update_font_setting(self, font_setting: FontSetting):
        session = self.get_db_session()
        try:
            query = session.query(FontSetting).filter_by(
                name=font_setting.name
            ).first()
            if query:
                for key in font_setting.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(font_setting, key))
            else:
                session.add(font_setting)
            session.commit()
        finally:
            session.close()

    #######################################
    ### AI MODELS ###
    #######################################
    def load_ai_models(self) -> List[AIModels]:
        session = self.get_db_session()
        try:
            return session.query(AIModels).all()
        finally:
            session.close()

    def update_ai_models(self, models: List[AIModels]):
        for model in models:
            self.update_ai_model(model)

    def update_ai_model(self, model: AIModels):
        session = self.get_db_session()
        try:
            query = session.query(AIModels).filter_by(
                name=model.name,
                path=model.path,
                branch=model.branch,
                version=model.version,
                category=model.category,
                pipeline_action=model.pipeline_action,
                enabled=model.enabled,
                model_type=model.model_type,
                is_default=model.is_default
            ).first()
            if query:
                for key in model.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(model, key))
            else:
                session.add(model)
            session.commit()
        finally:
            session.close()

    #######################################
    ### CHATBOTS ###
    #######################################
    def load_chatbots(self) -> List[Chatbot]:
        session = self.get_db_session()
        try:
            settings = session.query(Chatbot).all()
            return settings
        finally:
            session.close()

    def delete_chatbot_by_name(self, chatbot_name):
        session = self.get_db_session()
        try:
            session.query(Chatbot).filter_by(name=chatbot_name).delete()
            session.commit()
        finally:
            session.close()

    def create_chatbot(self, chatbot_name):
        session = self.get_db_session()
        try:
            new_chatbot = Chatbot(name=chatbot_name)
            session.add(new_chatbot)
            session.commit()
        finally:
            session.close()

    def update_chatbot(self, chatbot: Chatbot):
        session = self.get_db_session()
        try:
            query = session.query(Chatbot).filter_by(
                name=chatbot.name
            ).first()
            if query:
                for key in chatbot.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(chatbot, key))
            else:
                session.add(chatbot)
            session.commit()
        finally:
            session.close()

    def reset_path_settings(self):
        session = self.get_db_session()
        try:
            # Delete all entries from PathSettings
            session.query(PathSettings).delete()

            # Create a new PathSettings instance with default values
            self.set_default_values(PathSettings)
            # Commit the changes
            session.commit()
        finally:
            session.close()

    def set_default_values(self, model_name_):
        session = self.get_db_session()
        try:
            default_values = {}
            for column in model_name_.__table__.columns:
                if column.default is not None:
                    default_values[column.name] = column.default.arg
            session.execute(
                model_name_.__table__.insert(),
                [default_values]
            )
            session.commit()
        finally:
            session.close()

    #######################################
    ### LORA ###
    #######################################
    def load_lora(self) -> List[Lora]:
        session = self.get_db_session()
        try:
            return session.query(Lora).all()
        finally:
            session.close()

    def get_lora_by_name(self, name):
        session = self.get_db_session()
        try:
            return session.query(Lora).filter_by(name=name).first()
        finally:
            session.close()


    def add_lora(self, lora: Lora):
        session = self.get_db_session()
        try:
            session.add(lora)
            session.commit()
        finally:
            session.close()

    def delete_lora(self, lora: Lora):
        session = self.get_db_session()
        try:
            session.query(Lora).filter_by(name=lora.name).delete()
            session.commit()
        finally:
            session.close()

    def update_lora(self, lora: Lora):
        session = self.get_db_session()
        try:
            query = session.query(Lora).filter_by(name=lora.name).first()
            if query:
                for key in lora.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(lora, key))
            else:
                session.add(lora)
            session.commit()
        finally:
            session.close()

    def update_loras(self, loras: List[Lora]):
        session = self.get_db_session()
        try:
            for lora in loras:
                query = session.query(Lora).filter_by(name=lora.name).first()
                if query:
                    for key in lora.__dict__.keys():
                        if key != "_sa_instance_state":
                            setattr(query, key, getattr(lora, key))
                else:
                    session.add(lora)
            session.commit()
        finally:
            session.close()

    def create_lora(self, lora: Lora):
        session = self.get_db_session()
        try:
            session.add(lora)
            session.commit()
        finally:
            session.close()

    def delete_lora_by_name(self, lora_name, version):
        session = self.get_db_session()
        try:
            session.query(Lora).filter_by(name=lora_name, version=version).delete()
            session.commit()
        finally:
            session.close()

    #######################################
    ### EMBEDDINGS ###
    #######################################
    def delete_embedding(self, embedding: Embedding):
        session = self.get_db_session()
        try:
            session.query(Embedding).filter_by(
                name=embedding.name,
                path=embedding.path,
                branch=embedding.branch,
                version=embedding.version,
                category=embedding.category,
                pipeline_action=embedding.pipeline_action,
                enabled=embedding.enabled,
                model_type=embedding.model_type,
                is_default=embedding.is_default
            ).delete()
            session.commit()
        finally:
            session.close()

    def load_embeddings(self) -> List[Embedding]:
        session = self.get_db_session()
        try:
            return session.query(Embedding).all()
        finally:
            session.close()

    def update_embeddings(self, embeddings: List[Embedding]):
        session = self.get_db_session()
        try:
            for embedding in embeddings:
                query = session.query(Embedding).filter_by(
                    name=embedding.name,
                    path=embedding.path,
                    branch=embedding.branch,
                    version=embedding.version,
                    category=embedding.category,
                    pipeline_action=embedding.pipeline_action,
                    enabled=embedding.enabled,
                    model_type=embedding.model_type,
                    is_default=embedding.is_default
                ).first()
                if query:
                    for key in embedding.__dict__.keys():
                        if key != "_sa_instance_state":
                            setattr(query, key, getattr(embedding, key))
                else:
                    session.add(embedding)
            session.commit()
        finally:
            session.close()

    def get_embedding_by_name(self, name):
        session = self.get_db_session()
        try:
            return session.query(Embedding).filter_by(name=name).first()
        finally:
            session.close()

    def add_embedding(self, embedding: Embedding):
        session = self.get_db_session()
        try:
            session.add(embedding)
            session.commit()
        finally:
            session.close()

    #######################################
    ### PROMPT TEMPLATES ###
    #######################################
    def load_prompt_templates(self) -> List[PromptTemplate]:
        session = self.get_db_session()
        try:
            return session.query(PromptTemplate).all()
        finally:
            session.close()

    def get_prompt_template_by_name(self, name) -> PromptTemplate:
        session = self.get_db_session()
        try:
            return session.query(PromptTemplate).filter_by(template_name=name).first()
        finally:
            session.close()


    #######################################
    ### CONTROLNET MODELS ###
    #######################################
    def load_controlnet_models(self) -> List[ControlnetModel]:
        session = self.get_db_session()
        try:
            return session.query(ControlnetModel).all()
        finally:
            session.close()

    def controlnet_model_by_name(self, name) -> ControlnetModel:
        session = self.get_db_session()
        try:
            return session.query(ControlnetModel).filter_by(name=name).first()
        finally:
            session.close()

    def load_pipelines(self) -> List[PipelineModel]:
        session = self.get_db_session()
        try:
            return session.query(PipelineModel).all()
        finally:
            session.close()


    def load_shortcut_keys(self) -> List[ShortcutKeys]:
        session = self.get_db_session()
        try:
            return session.query(ShortcutKeys).all()
        finally:
            session.close()


    def load_window_settings(self) -> WindowSettings:
        session = self.get_db_session()
        try:
            return session.query(WindowSettings).first()
        finally:
            session.close()


    def save_window_settings(self, window_settings: WindowSettings):
        session = self.get_db_session()
        try:
            query = session.query(WindowSettings).first()
            if query:
                for key in window_settings.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(window_settings, key))
            else:
                session.add(window_settings)
            session.commit()
        finally:
            session.close()
