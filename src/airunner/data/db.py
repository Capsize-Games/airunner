from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.models import ControlnetModel, Pipeline, \
    AIModel, ImageFilter, ImageFilterValue
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
        if not my_session.query(ControlnetModel).first():
            do_stamp_alembic = True

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
