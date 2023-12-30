from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.generator_bootstrap_data import sections_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.llm import seed_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.prompt_bootstrap_data import prompt_bootstrap_data, style_bootstrap_data, \
    variable_bootstrap_data
from airunner.data.models import ControlnetModel, LLMPromptTemplate, Pipeline, Document, Settings, PromptGeneratorSetting, \
    GeneratorSetting, SplitterSection, GridSettings, MetadataSettings, PathSettings, MemorySettings, AIModel, \
    ImageFilter, ImageFilterValue, BrushSettings, Prompt, PromptVariable, PromptCategory, PromptOption, \
    PromptVariableCategory, PromptVariableCategoryWeight, PromptStyleCategory, PromptStyle, Scheduler, ActionScheduler, \
    DeterministicSettings, ActiveGridSettings, TabSection, PromptBuilder, CanvasSettings, \
    LLMGeneratorSetting, LLMGenerator, LLMModelVersion
from airunner.utils import get_session
from alembic.config import Config
from alembic import command
import os
import configparser

session = get_session()

# check if database is blank:
if not session.query(Prompt).first():

    # Add Prompt objects
    for prompt_option, data in prompt_bootstrap_data.items():
        category = PromptCategory(name=prompt_option, negative_prompt=data["negative_prompt"])
        prompt = Prompt(
            name=f"Standard {prompt_option} prompt",
            category=category
        )
        session.add(prompt)
        session.commit()
        prompt_id = prompt.id

        prompt_variables = []
        for category_name, variable_values in data["variables"].items():
            # add prompt category
            cat = session.query(PromptVariableCategory).filter_by(name=category_name).first()
            if not cat:
                cat = PromptVariableCategory(name=category_name)
                session.add(cat)
                session.commit()

            # add prompt variable category weight
            weight = session.query(PromptVariableCategoryWeight).filter_by(
                prompt_category=category,
                variable_category=cat
            ).first()
            if not weight:
                try:
                    weight_value = data["weights"][category_name]
                except KeyError:
                    weight_value = 1.0
                weight = PromptVariableCategoryWeight(
                    prompt_category=category,
                    variable_category=cat,
                    weight=weight_value
                )
                session.add(weight)
                session.commit()

            # add prompt variables
            for var in variable_values:
                session.add(PromptVariable(
                    value=var,
                    prompt_category=category,
                    variable_category=cat
                ))
            session.commit()

        def insert_variables(variables, prev_object=None):
            for option in variables:
                text = option.get("text", None)
                cond = option.get("cond", "")
                else_cond = option.get("else", "")
                next_cond = option.get("next", None)
                or_cond = option.get("or_cond", None)
                prompt_option = PromptOption(
                    text=text,
                    cond=cond,
                    else_cond=else_cond,
                    or_cond=or_cond,
                    prompt_id=prompt_id
                )
                if prev_object:
                    session.add(prompt_option)
                    session.commit()
                    prev_object.next_cond_id = prompt_option.id
                    session.add(prev_object)
                    session.commit()
                    prev_object = prompt_option
                else:
                    session.add(prompt_option)
                    session.commit()
                    prev_object = prompt_option
                if next_cond:
                    prev_object = insert_variables(
                        variables=next_cond,
                        prev_object=prev_object,
                    )
            return prev_object

        insert_variables(data["builder"])

        session.commit()

    for variable_category, data in variable_bootstrap_data.items():
        category = session.query(PromptVariableCategory).filter_by(name=variable_category).first()
        if not category:
            category = PromptVariableCategory(name=variable_category)
            session.add(category)
            session.commit()
        for variable in data:
            session.add(PromptVariable(
                value=variable,
                variable_category=category
            ))
        session.commit()

    # Add PromptStyle objects
    for style_category, data in style_bootstrap_data.items():
        category = PromptStyleCategory(name=style_category, negative_prompt=data["negative_prompt"])
        session.add(category)
        session.commit()
        for style in data["styles"]:
            session.add(PromptStyle(
                name=style,
                style_category=category
            ))
        session.commit()

    # Add ControlnetModel objects
    for name, path in controlnet_bootstrap_data.items():
        session.add(ControlnetModel(name=name, path=path))
    session.commit()


    # Add AIModel objects
    for model_data in model_bootstrap_data:
        session.add(AIModel(**model_data))
    session.commit()


    # Add Pipeline objects
    for pipeline_data in pipeline_bootstrap_data:
        session.add(Pipeline(**pipeline_data))
    session.commit()


    # Add PathSettings objects
    session.add(PathSettings())
    session.commit()


    # Add BrushSettings objects
    session.add(BrushSettings())
    session.commit()


    # Add GridSettings objects
    session.add(GridSettings())
    session.commit()

    session.add(DeterministicSettings())
    session.commit()


    # Add MetadataSettings objects
    session.add(MetadataSettings())
    session.commit()


    # Add MemorySettings objects
    session.add(MemorySettings())
    session.commit()

    # Add ActiveGridSettings object
    session.add(ActiveGridSettings())
    session.commit()


    # Add ImageFilter objects
    for filter in imagefilter_bootstrap_data:
        image_filter = ImageFilter(
            display_name=filter[0],
            name=filter[1],
            filter_class=filter[2]
        )
        for filter_value in filter[3]:
            image_filter.image_filter_values.append(ImageFilterValue(
                name=filter_value[0],
                value=filter_value[1],
                value_type=filter_value[2],
                min_value=filter_value[3] if len(filter_value) > 3 else None,
                max_value=filter_value[4] if len(filter_value) > 4 else None
            ))
        session.add(image_filter)
        session.commit()

    image_filter = session.query(ImageFilter).filter_by(name='color_balance').first()

    # Access its image_filter_values
    filter_values = image_filter.image_filter_values

    # Add Document object
    settings = Settings(nsfw_filter=True)
    settings.prompt_generator_settings.append(
        PromptGeneratorSetting(
            name="Prompt A",
            active=True,
            settings_id=settings.id
        )
    )
    settings.prompt_generator_settings.append(
        PromptGeneratorSetting(
            name="Prompt B",
            settings_id=settings.id
        )
    )
    settings.splitter_sizes.append(SplitterSection(
        name="content_splitter",
        order=0,
        size=390
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="content_splitter",
        order=1,
        size=512
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="content_splitter",
        order=2,
        size=200
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="content_splitter",
        order=3,
        size=64
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main_splitter",
        order=0,
        size=520
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main_splitter",
        order=1,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="canvas_splitter",
        order=0,
        size=520
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="canvas_splitter",
        order=1,
        size=-1
    ))
    session.add(settings)

    settings.brush_settings = session.query(BrushSettings).first()
    settings.path_settings = session.query(PathSettings).first()
    settings.grid_settings = session.query(GridSettings).first()
    settings.deterministic_settings = session.query(DeterministicSettings).first()
    settings.metadata_settings = session.query(MetadataSettings).first()
    settings.memory_settings = session.query(MemorySettings).first()
    settings.active_grid_settings = session.query(ActiveGridSettings).first()

    active_grid_colors = {
        "stablediffusion": {
            "border": {
                "txt2img": "#00FF00",
                "outpaint": "#00FFFF",
                "depth2img": "#0000FF",
                "pix2pix": "#FFFF00",
                "upscale": "#00FFFF",
                "superresolution": "#FF00FF",
                "txt2vid": "#999999",
            },
            # choose complimentary colors for the fill
            "fill": {
                "txt2img": "#FF0000",
                "outpaint": "#FF00FF",
                "depth2img": "#FF8000",
                "pix2pix": "#8000FF",
                "upscale": "#00FF80",
                "superresolution": "#00FF00",
                "txt2vid": "#000000",

            }
        },
        "kandinsky": {
            "border": {
                "txt2img": "#FF0000",
                "outpaint": "#FF0000",
            },
            "fill": {
                "txt2img": "#FF0000",
                "outpaint": "#FF00FF",
            }
        },
        "shapegif": {
            "border": {
                "txt2img": "#FF0000",
            },
            "fill": {
                "txt2img": "#FF0000",
            }
        },
    }

    for generator_name, generator_sections in sections_bootstrap_data.items():
        for generator_section in generator_sections:
            settings.generator_settings.append(GeneratorSetting(
                section=generator_section,
                generator_name=generator_name,
                active_grid_border_color=active_grid_colors[generator_name]["border"][generator_section],
                active_grid_fill_color=active_grid_colors[generator_name]["fill"][generator_section]
            ))

    session.add(Document(
        name="Untitled",
        settings=settings,
        active=True
    ))
    session.commit()


    available_schedulers = {}
    for scheduler_data in [
        ("Euler a", "EULER_ANCESTRAL"),
        ("Euler", "EULER"),
        ("LMS", "LMS"),
        ("Heun", "HEUN"),
        ("DPM2", "DPM2"),
        ("DPM++ 2M", "DPM_PP_2M"),
        ("DPM2 Karras", "DPM2_K"),
        ("DPM2 a Karras", "DPM2_A_K"),
        ("DPM++ 2M Karras", "DPM_PP_2M_K"),
        ("DPM++ 2M SDE Karras", "DPM_PP_2M_SDE_K"),
        ("DDIM", "DDIM"),
        ("UniPC", "UNIPC"),
        ("DDPM", "DDPM"),
        ("DEIS", "DEIS"),
        ("DPM 2M SDE Karras", "DPM_2M_SDE_K"),
        ("PLMS", "PLMS"),
    ]:
        obj = Scheduler(
            name=scheduler_data[1],
            display_name=scheduler_data[0]
        )
        session.add(obj)
        available_schedulers[scheduler_data[1]] = obj
    session.commit()

    generator_sections = {
        "stablediffusion": {
            "upscale": ["EULER"],
            "superresolution": ["DDIM", "LMS", "PLMS"],
        },
        "kandinsky": {
            "txt2img": [
                "EULER_ANCESTRAL",
                "DPM2_A_K",
                "DDPM",
                "DPM_PP_2M",
                "DPM_PP_2M_K",
                "DPM_2M_SDE_K",
                "DPM_PP_2M_SDE_K",
                "DDIM",
            ],
            "outpaint": [
                "EULER_ANCESTRAL",
                "DPM2_A_K",
                "DDPM",
                "DPM_PP_2M",
                "DPM_PP_2M_K",
                "DPM_2M_SDE_K",
                "DPM_PP_2M_SDE_K",
                "DDIM",
            ]
        },
        "shapegif": {
            "txt2img": ["HEUN"],
        }
    }

    # add all of the schedulers for the defined generator sections
    for generator, sections in generator_sections.items():
        for section, schedulers in sections.items():
            for scheduler in schedulers:
                session.add(ActionScheduler(
                    section=section,
                    generator_name=generator,
                    scheduler_id=session.query(Scheduler).filter_by(name=scheduler).first().id
                ))
    session.commit()

    # add the rest of the stable diffusion schedulers
    for k, v in available_schedulers.items():
        for section in [
            "txt2img", "depth2img", "pix2pix", "vid2vid",
            "outpaint", "controlnet", "txt2vid"
        ]:
            obj = ActionScheduler(
                section=section,
                generator_name="stablediffusion",
                scheduler_id=v.id
            )
            session.add(obj)
    session.commit()

    # create tab sections
    session.add(TabSection(
        panel="center_tab",
        active_tab="Canvas"
    ))
    session.add(TabSection(
        panel="tool_tab_widget",
        active_tab="Embeddings"
    ))
    session.add(TabSection(
        panel="batches_tab",
        active_tab="Deterministic Batches"
    ))
    session.add(TabSection(
        panel="prompt_builder.ui.tabs",
        active_tab="0"
    ))
    session.commit()

    session.add(PromptBuilder(
        name="Prompt A",
        active=True
    ))
    session.add(PromptBuilder(
        name="Prompt B",
        active=True
    ))
    session.commit()

    session.add(CanvasSettings())
    session.commit()


    for generator_name, generator_data in seed_data.items():
        generator = LLMGenerator(name=generator_name)
        session.add(generator)

        # create GeneratorSetting with property, value and property_type based on value type
        setting = LLMGeneratorSetting()
        setting.generator = generator
        for k, v in generator_data["generator_settings"].items():
            setting.__setattr__(k, v)
        session.add(setting)

        if "model_versions" in generator_data:
            model_versions = []
            for name in generator_data["model_versions"]:
                print("Name", name)
                model_versions.append(LLMModelVersion(name=name))

        for version in model_versions:
            generator.model_versions.append(version)

        session.add(generator)
        session.commit()

    from airunner.data.bootstrap.prompt_templates import prompt_template_seed_data
    for data in prompt_template_seed_data:
        prompt_template = LLMPromptTemplate(
            name=data["name"],
            template=data["template"]
        )
        session.add(prompt_template)
        session.commit()


    default_models = [
        {
            "name": "Stable Diffusion 2.1 512",
            "pipeline": "txt2img",
            "toolname": "txt2img"
        },
        {
            "name": "Stable Diffusion Inpaint 2",
            "pipeline": "outpaint",
            "toolname": "outpaint"
        },
        {
            "name": "Stable Diffusion Depth2Img",
            "pipeline": "depth2img",
            "toolname": "depth2img"
        },
        {
            "name": "Stable Diffusion 1.5",
            "pipeline": "controlnet",
            "toolname": "controlnet"
        },
        {
            "name": "Stability AI 4x resolution",
            "pipeline": "superresolution",
            "toolname": "superresolution"
        },
        {
            "name": "Instruct pix2pix",
            "pipeline": "pix2pix",
            "toolname": "pix2pix"
        },
        {
            "name": "SD Image Variations",
            "pipeline": "vid2vid",
            "toolname": "vid2vid"
        },
        {
            "name": "sd-x2-latent-upscaler",
            "pipeline": "upscale",
            "toolname": "upscale"
        },
        {
            "name": "Inpaint vae",
            "pipeline": "inpaint_vae",
            "toolname": "inpaint_vae"
        },
        {
            "name": "Salesforce InstructBlip Flan T5 XL",
            "pipeline": "visualqa",
            "toolname": "visualqa"
        },
        {
            "name": "Llama 2 7b Chat",
            "pipeline": "casuallm",
            "toolname": "casuallm"
        },
        {
            "name": "Flan T5 XL",
            "pipeline": "seq2seq",
            "toolname": "prompt_generation"
        },
    ]

HERE = os.path.abspath(os.path.dirname(__file__))
alembic_ini_path = os.path.join(HERE, "../alembic.ini")

config = configparser.ConfigParser()
config.read(alembic_ini_path)

home_dir = os.path.expanduser("~")
db_path = f'sqlite:///{home_dir}/.airunner/airunner.db'

config.set('alembic', 'sqlalchemy.url', db_path)

with open(alembic_ini_path, 'w') as configfile:
    config.write(configfile)

alembic_cfg = Config(alembic_ini_path)
command.upgrade(alembic_cfg, "head")