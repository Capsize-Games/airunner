class PipelineMixin:
    def get_pipeline_classname(self, pipeline_action, version, category):
        try:
            return self.get_pipelines(pipeline_action=pipeline_action, version=version, category=category)[0]["classname"]
        except:
            return None
    
    def get_pipelines(self, pipeline_action=None, version=None, category=None):
        pipelines = self.settings["pipelines"]
        if pipeline_action:
            pipelines = [pipeline for pipeline in pipelines if pipeline["pipeline_action"] == pipeline_action]
        if version:
            pipelines = [pipeline for pipeline in pipelines if pipeline["version"] == version]
        if category:
            pipelines = [pipeline for pipeline in pipelines if pipeline["category"] == category]
        return pipelines