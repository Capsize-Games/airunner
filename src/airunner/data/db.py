from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.generator_bootstrap_data import sections_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.prompt_bootstrap_data import prompt_bootstrap_data, style_bootstrap_data, \
    variable_bootstrap_data
from airunner.data.models import Base, ControlnetModel, Pipeline, Document, Settings, PromptGeneratorSetting, \
    GeneratorSetting, SplitterSection, GridSettings, MetadataSettings, PathSettings, MemorySettings, AIModel, \
    ImageFilter, ImageFilterValue, BrushSettings, Prompt, PromptVariable, PromptCategory, PromptOption, \
    PromptVariableCategory, PromptVariableCategoryWeight, PromptStyleCategory, PromptStyle

engine = create_engine('sqlite:///airunner.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


if not session.query(Prompt).first():
    for prompt_option, data in prompt_bootstrap_data.items():
        category = PromptCategory(name=prompt_option)
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

    # add extra variables to database
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


if not session.query(PromptStyle).first():
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


if not session.query(ControlnetModel).first():
    for name, path in controlnet_bootstrap_data.items():
        session.add(ControlnetModel(name=name, path=path))
    session.commit()


if not session.query(AIModel).first():
    for model_data in model_bootstrap_data:
        session.add(AIModel(**model_data))
    session.commit()


if not session.query(Pipeline).first():
    for pipeline_data in pipeline_bootstrap_data:
        session.add(Pipeline(**pipeline_data))
    session.commit()


if not session.query(PathSettings).first():
    session.add(PathSettings())
    session.commit()


if not session.query(BrushSettings).first():
    session.add(BrushSettings())
    session.commit()


if not session.query(GridSettings).first():
    session.add(GridSettings())
    session.commit()


if not session.query(MetadataSettings).first():
    session.add(MetadataSettings())
    session.commit()


if not session.query(MemorySettings).first():
    session.add(MemorySettings())
    session.commit()


if not session.query(ImageFilter).first():
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


if not session.query(Document).first():
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
        name="main",
        order=0,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main",
        order=1,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main",
        order=2,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="center",
        order=0,
        size=520
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="center",
        order=1,
        size=-1
    ))
    session.add(settings)

    settings.brush_settings = session.query(BrushSettings).first()
    settings.path_settings = session.query(PathSettings).first()
    settings.grid_settings = session.query(GridSettings).first()
    settings.metadata_settings = session.query(MetadataSettings).first()
    settings.memory_settings = session.query(MemorySettings).first()

    for section in sections_bootstrap_data:
        for generator_name in sections_bootstrap_data[section]:
            settings.generator_settings.append(GeneratorSetting(
                section=section,
                generator_name=generator_name
            ))

    session.add(Document(
        name="Untitled",
        settings=settings
    ))
    session.commit()
