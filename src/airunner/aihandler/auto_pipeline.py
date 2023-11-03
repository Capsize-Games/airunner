from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.settings_manager import SettingsManager


class AutoImport:
    def __init__(self, requested_action, pipeline_action="", category=None):
        self.__class__ = AutoImport.class_object(requested_action, pipeline_action, category)

    @staticmethod
    def from_pretrained(requested_action, **kwargs):
        class_object = kwargs.pop("class_object", None)
        model = kwargs.pop("model", None)
        model_data = kwargs.pop("model_data")
        pipeline_action = kwargs.pop("pipeline_action", None)
        category = kwargs.pop("category", None)
        if class_object is None:
            class_object = AutoImport.class_object(
                requested_action, 
                model_data, 
                pipeline_action,
            )
        if class_object is None:
            return None
        return class_object.from_pretrained(model, **kwargs)

    @staticmethod
    def class_object(
        requested_action,
        model_data,
        pipeline_action,
        category=None,
        single_file=False
    ):
        version = model_data["version"]
        category = category if category else model_data["category"]
        if pipeline_action == "txt2img" and requested_action == "img2img":
            pipeline_action = "img2img"
        settings_manager = SettingsManager()
        pipeline = settings_manager.available_pipeline_by_section(pipeline_action, version, category)

        try:
            if single_file and pipeline.singlefile_classname != "":
                classname = pipeline.singlefile_classname
            else:
                classname = pipeline.classname
        except KeyError:
            logger.error(f"Failed to find classname for pipeline_action {pipeline_action} {version} {category}")
            return
        pipeline_classname = classname.split(".")
        module = None
        for index, module_name in enumerate(pipeline_classname):
            if index == 0:
                module = __import__(module_name)
            else:
                module = getattr(module, module_name)
        return module
