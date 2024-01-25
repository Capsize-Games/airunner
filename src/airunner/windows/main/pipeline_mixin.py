from airunner.service_locator import ServiceLocator


class PipelineMixin:
    def __init__(self, *args, **kwargs):
        ServiceLocator.register(ServiceCode.GET_PIPELINE_CLASSNAME, self.get_pipeline_classname)
        ServiceLocator.register(ServiceCode.PIPELINE_ACTIONS, self.pipeline_actions)
        ServiceLocator.register(ServiceCode.GET_PIPELINES, self.get_pipelines)

    def pipeline_get_by_filter(self, filter_dict):
        return [item for item in self.settings["pipelines"] if all(item.get(k) == v for k, v in filter_dict.items())]

    def pipeline_create(self, item):
        settings = self.settings
        settings["pipelines"].append(item)
        self.settings = settings

    def pipeline_update(self, item):
        settings = self.settings
        for i, existing_item in enumerate(settings["pipelines"]):
            if existing_item['name'] == item['name']:
                settings["pipelines"][i] = item
                self.settings = settings
                break

    def pipeline_delete(self, item):
        settings = self.settings
        settings["pipelines"] = [existing_item for existing_item in self.settings["pipelines"] if existing_item['name'] != item['name']]
        self.settings = settings

    def get_pipeline_classname(self, pipeline_action, version, category):
        pipelines = self.get_pipelines(pipeline_action, version, category)
        if len(pipelines) > 0:
            return pipelines[0]["classname"]
        else:
            return None
    
    def get_pipelines(self, pipeline_action=None, version=None, category=None):
        pipelines = self.settings["pipelines"]
        if pipeline_action:
            pipelines = self.pipeline_get_by_filter({"pipeline_action": pipeline_action})
        if version:
            pipelines = self.pipeline_get_by_filter({"version": version})
        if category:
            pipelines = self.pipeline_get_by_filter({"category": category})
        return pipelines

    def available_pipeline_by_section(self, section):
        return [pipeline["name"] for pipeline in self.settings["pipelines"] if pipeline["section"] == section]

    def available_pipeline_by_action_version_category(self, pipeline_action, version, category):
        return [pipeline["name"] for pipeline in self.settings["pipelines"] if pipeline["pipeline_action"] == pipeline_action and pipeline["version"] == version and pipeline["category"] == category]

    def pipeline_actions(self):
        return [pipeline["pipeline_action"] for pipeline in self.settings["pipelines"]]