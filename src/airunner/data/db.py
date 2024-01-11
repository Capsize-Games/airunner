from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.llm import seed_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.prompt_bootstrap_data import prompt_bootstrap_data, style_bootstrap_data, \
    variable_bootstrap_data
from airunner.data.models import ControlnetModel, LLMPromptTemplate, Pipeline, Document, \
    GeneratorSetting, MetadataSettings, MemorySettings, AIModel, \
    ImageFilter, ImageFilterValue, Prompt, PromptVariable, PromptCategory, PromptOption, \
    PromptVariableCategory, PromptVariableCategoryWeight, PromptStyleCategory, PromptStyle, Scheduler, ActionScheduler, \
    DeterministicSettings, ActiveGridSettings, CanvasSettings, \
    LLMGeneratorSetting, LLMGenerator, LLMModelVersion, StandardImageWidgetSettings
from airunner.data.session_scope import session_scope, engine
from alembic.config import Config
from alembic import command
import os
import configparser


def prepare_database():
    from airunner.data.models import Base
    Base.metadata.create_all(engine)

    with session_scope() as my_session:
        do_stamp_alembic = False

        # check if database is blank:
        if not my_session.query(Prompt).first():
            do_stamp_alembic = True

            standard_image_widget = StandardImageWidgetSettings()
            my_session.add(standard_image_widget)

            # Add Prompt objects
            for prompt_option, data in prompt_bootstrap_data.items():
                category = PromptCategory(name=prompt_option, negative_prompt=data["negative_prompt"])
                prompt = Prompt(
                    name=f"Standard {prompt_option} prompt",
                    category=category
                )
                my_session.add(prompt)
                
                prompt_id = prompt.id

                prompt_variables = []
                for category_name, variable_values in data["variables"].items():
                    # add prompt category
                    cat = my_session.query(PromptVariableCategory).filter_by(name=category_name).first()
                    if not cat:
                        cat = PromptVariableCategory(name=category_name)
                        my_session.add(cat)
                        

                    # add prompt variable category weight
                    weight = my_session.query(PromptVariableCategoryWeight).filter_by(
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
                        my_session.add(weight)
                        

                    # add prompt variables
                    for var in variable_values:
                        my_session.add(PromptVariable(
                            value=var,
                            prompt_category=category,
                            variable_category=cat
                        ))
                    

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
                            my_session.add(prompt_option)
                            
                            prev_object.next_cond_id = prompt_option.id
                            my_session.add(prev_object)
                            
                            prev_object = prompt_option
                        else:
                            my_session.add(prompt_option)
                            
                            prev_object = prompt_option
                        if next_cond:
                            prev_object = insert_variables(
                                variables=next_cond,
                                prev_object=prev_object,
                            )
                    return prev_object

                insert_variables(data["builder"])

                

            for variable_category, data in variable_bootstrap_data.items():
                category = my_session.query(PromptVariableCategory).filter_by(name=variable_category).first()
                if not category:
                    category = PromptVariableCategory(name=variable_category)
                    my_session.add(category)
                    
                for variable in data:
                    my_session.add(PromptVariable(
                        value=variable,
                        variable_category=category
                    ))
                

            # Add PromptStyle objects
            for style_category, data in style_bootstrap_data.items():
                category = PromptStyleCategory(name=style_category, negative_prompt=data["negative_prompt"])
                my_session.add(category)
                
                for style in data["styles"]:
                    my_session.add(PromptStyle(
                        name=style,
                        style_category=category
                    ))
                

            # Add ControlnetModel objects
            for name, path in controlnet_bootstrap_data.items():
                my_session.add(ControlnetModel(name=name, path=path))
            


            # Add AIModel objects
            for model_data in model_bootstrap_data:
                my_session.add(AIModel(**model_data))
            


            # Add Pipeline objects
            for pipeline_data in pipeline_bootstrap_data:
                my_session.add(Pipeline(**pipeline_data))
            


            my_session.add(DeterministicSettings())
            


            # Add MetadataSettings objects
            my_session.add(MetadataSettings())
            


            # Add MemorySettings objects
            my_session.add(MemorySettings())
            

            # Add ActiveGridSettings object
            my_session.add(ActiveGridSettings())
            

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
                my_session.add(image_filter)
                

            image_filter = my_session.query(ImageFilter).filter_by(name='color_balance').first()

            # Access its image_filter_values
            filter_values = image_filter.image_filter_values

            # Add Document object
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
            }

            generator_section = "txt2img"
            generator_name = "stablediffusion"
            my_session.add(GeneratorSetting(
                section=generator_section,
                generator_name=generator_name,
                active_grid_border_color=active_grid_colors[generator_name]["border"][generator_section],
                active_grid_fill_color=active_grid_colors[generator_name]["fill"][generator_section]
            ))

            my_session.add(Document(
                name="Untitled",
                active=True
            ))
            


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
                my_session.add(obj)
                available_schedulers[scheduler_data[1]] = obj
            

            generator_sections = {
                "stablediffusion": {
                    "upscale": ["EULER"],
                    "superresolution": ["DDIM", "LMS", "PLMS"],
                },
            }

            # add all of the schedulers for the defined generator sections
            for generator, sections in generator_sections.items():
                for section, schedulers in sections.items():
                    for scheduler in schedulers:
                        my_session.add(ActionScheduler(
                            section=section,
                            generator_name=generator,
                            scheduler_id=my_session.query(Scheduler).filter_by(name=scheduler).first().id
                        ))
            

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
                    my_session.add(obj)
            
                        

            my_session.add(CanvasSettings())
            


            for generator_name, generator_data in seed_data.items():
                generator = LLMGenerator(name=generator_name)
                my_session.add(generator)

                # create GeneratorSetting with property, value and property_type based on value type
                setting = LLMGeneratorSetting()
                setting.generator = generator
                for k, v in generator_data["generator_settings"].items():
                    setting.__setattr__(k, v)
                my_session.add(setting)

                if "model_versions" in generator_data:
                    model_versions = []
                    for name in generator_data["model_versions"]:
                        print("Name", name)
                        model_versions.append(LLMModelVersion(name=name))

                for version in model_versions:
                    generator.model_versions.append(version)

                my_session.add(generator)
                

            from airunner.data.bootstrap.prompt_templates import prompt_template_seed_data
            for data in prompt_template_seed_data:
                prompt_template = LLMPromptTemplate(
                    name=data["name"],
                    template=data["template"]
                )
                my_session.add(prompt_template)
                

    HERE = os.path.abspath(os.path.dirname(__file__)) 
    alembic_ini_path = os.path.join(HERE, "../alembic.ini")

    config = configparser.ConfigParser()
    config.read(f"{alembic_ini_path}.config")

    home_dir = os.path.expanduser("~")
    db_path = f'sqlite:///{home_dir}/.airunner/airunner.db'

    config.set('alembic', 'sqlalchemy.url', db_path)
    with open(alembic_ini_path, 'w') as configfile:
        config.write(configfile)
    alembic_cfg = Config(alembic_ini_path)
    if not do_stamp_alembic:
        command.upgrade(alembic_cfg, "head")
    else:
        command.stamp(alembic_cfg, "head")
