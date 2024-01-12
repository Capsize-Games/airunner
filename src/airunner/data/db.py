from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.llm import seed_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.models import ControlnetModel, LLMPromptTemplate, Pipeline, Document, \
    AIModel, \
    ImageFilter, ImageFilterValue, Scheduler, ActionScheduler, \
    LLMModelVersion, StandardImageWidgetSettings
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
        if not my_session.query(Document).first():
            do_stamp_alembic = True

            standard_image_widget = StandardImageWidgetSettings()
            my_session.add(standard_image_widget)


            # Add ControlnetModel objects
            for name, path in controlnet_bootstrap_data.items():
                my_session.add(ControlnetModel(name=name, path=path))
            


            # Add AIModel objects
            for model_data in model_bootstrap_data:
                my_session.add(AIModel(**model_data))
            


            # Add Pipeline objects
            for pipeline_data in pipeline_bootstrap_data:
                my_session.add(Pipeline(**pipeline_data))
            
            

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
            
                        

            for generator_name, generator_data in seed_data.items():
                if "model_versions" in generator_data:
                    model_versions = []
                    for name in generator_data["model_versions"]:
                        print("Name", name)
                        model_versions.append(LLMModelVersion(name=name))

                for version in model_versions:
                    generator.model_versions.append(version)

                my_session.add(generator)
                

            prompt_template = LLMPromptTemplate()
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
