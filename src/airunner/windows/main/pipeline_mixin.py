from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data


class PipelineMixin:
    def pipeline_get_by_filter(self, filter_dict):
        return [item for item in pipeline_bootstrap_data if all(item.get(k) == v for k, v in filter_dict.items())]

    def get_pipeline_classname(self, pipeline_action, version, category):
        pipelines = self.get_pipelines(pipeline_action, version, category)
        if len(pipelines) > 0:
            return pipelines[0]["classname"]
        else:
            return None
    
    def get_pipelines(self, pipeline_action=None, version=None, category=None):
        pipelines = pipeline_bootstrap_data
        if pipeline_action:
            pipelines = self.pipeline_get_by_filter({"pipeline_action": pipeline_action})
        if version:
            pipelines = self.pipeline_get_by_filter({"version": version})
        if category:
            pipelines = self.pipeline_get_by_filter({"category": category})
        return pipelines

    def available_pipeline_by_section(self, section):
        return [pipeline["name"] for pipeline in pipeline_bootstrap_data if pipeline["section"] == section]

    def available_pipeline_by_action_version_category(self, pipeline_action, version, category):
        return [pipeline["name"] for pipeline in pipeline_bootstrap_data if pipeline["pipeline_action"] == pipeline_action and pipeline["version"] == version and pipeline["category"] == category]

    def pipeline_actions(self):
        return [pipeline["pipeline_action"] for pipeline in pipeline_bootstrap_data]
