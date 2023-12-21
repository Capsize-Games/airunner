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
                category
            )
        if class_object is None:
            return None
        if "torch_dtype" in kwargs:
            del kwargs["torch_dtype"]
        try:
            return class_object.from_pretrained(model, **kwargs)
        except Exception as e:
            try_again = False
            if "Checkout your internet connection" in str(e):
                try_again = True
            elif "To enable repo look-ups" in str(e):
                try_again = True
            elif "No such file or directory" in str(e):
                try_again = True
            elif "does not appear to have a file named config.json" in str(e):
                try_again = True
            elif "Entry Not Found" in str(e):
                try_again = True
            if try_again:
                kwargs["local_files_only"] = False
                kwargs["class_object"] = class_object
                kwargs["model_data"] = model_data
                kwargs["model"] = model
                kwargs["pipeline_action"] = pipeline_action
                kwargs["category"] = category
                return AutoImport.from_pretrained(requested_action, **kwargs)

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
            if single_file and pipeline.singlefile_classname != "" and pipeline.singlefile_classname is not None:
                classname = pipeline.singlefile_classname
            else:
                classname = pipeline.classname
        except KeyError:
            logger.error(f"Failed to find classname for pipeline_action {pipeline_action} {version} {category}")
            return
        except AttributeError as e:
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
