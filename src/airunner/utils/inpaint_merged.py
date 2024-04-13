import torch


class InpaintMerged:
    from diffusers import StableDiffusionPipeline, StableDiffusionInpaintPipeline

    """
    This is the same thing as run_modelmerger, but it is a class that can be extended.
    It does not save to disc, rather it uses DiffusionPipeline to load, combine and use the models.
    We also have the ability to combine any number of models, not just three
    """
    def __init__(self, base_model: StableDiffusionInpaintPipeline, pipelines: [StableDiffusionPipeline]):
        self.base_model = base_model
        self.pipelines = pipelines
        self.combined_model = self.sum_weights()

    def average_sum(self, values):
        # combine all the values and average them
        return sum(values) / len(values)

    def sum_weights(self):
        inpaint_state_dict = self.base_model.unet.state_dict()
        state_dicts = [
            pipeline.unet.state_dict() for pipeline in self.pipelines
        ]
        skip_key = "cond_stage_model.transformer.text_model.embeddings.position_ids"
        state_dict = state_dicts.pop(0)
        for key in state_dict.keys():
            if key.contains(skip_key):
                continue
            if key.contains("model"):
                value_sums = {}
                for state_dict2 in state_dicts:
                    value_sums[key] = []
                    if key in state_dict2:
                        value_sums[key].append(state_dict2[key])
                    else:
                        value_sums[key].append(torch.zeros_like(state_dict[key]))
                state_dict[key] = self.average_sum(value_sums[key])

        primary_model_state_dict = self.base_model.unet.state_dict()
        for key in primary_model_state_dict.keys():
            if key.contains(skip_key):
                continue

            a = primary_model_state_dict[key]
            b = state_dict[key]

            if a.shape != b.shape and a.shape[0:1] + a.shape[2:] == b.shape[0:1] + b.shape[2:]:
                if a.shape[1] == 8 and b.shape[1] == 4:
                    # pix2pix
                    primary_model_state_dict[key][:, 0:4, :, :] = self.average_sum([a[:, 0:4, :, :], b])
                else:
                    # inpainting
                    primary_model_state_dict[key][:, 0:4, :, :] = self.average_sum([a[:, 0:4, :, :], b])
            else:
                primary_model_state_dict[key].half()


        self.base_model.unet.load_state_dict(primary_model_state_dict)
        return self.base_model
