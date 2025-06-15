__all__ = [
    "ExternalConditionStoppingCriteria",
    "HtmlFileReader",
    "RAGMixin",
    "WeatherMixin",
]


def __getattr__(name):
    if name == "ExternalConditionStoppingCriteria":
        from .external_condition_stopping_criteria import (
            ExternalConditionStoppingCriteria,
        )

        return ExternalConditionStoppingCriteria
    elif name == "HtmlFileReader":
        from .html_file_reader import HtmlFileReader

        return HtmlFileReader
    elif name == "RAGMixin":
        from .rag_mixin import RAGMixin

        return RAGMixin
    elif name == "WeatherMixin":
        from .weather_mixin import WeatherMixin

        return WeatherMixin
    raise AttributeError(f"module {__name__} has no attribute {name}")
