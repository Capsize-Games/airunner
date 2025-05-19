from lingua import Language, LanguageDetectorBuilder
from airunner.enums import AvailableLanguage


def detect_language(txt: str) -> str:
    languages = [
        Language.ENGLISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.SPANISH,
        Language.KOREAN,
        Language.RUSSIAN,
        Language.SPANISH,
        Language.CHINESE,
        Language.JAPANESE,
    ]
    detector = LanguageDetectorBuilder.from_languages(*languages).build()
    language = detector.detect_language_of(txt)
    name = language.iso_code_639_1.name
    if name == "JA":
        return AvailableLanguage.JP.value
    if name == "KO":
        return AvailableLanguage.KR.value
    try:
        return AvailableLanguage(name).value
    except KeyError:
        print(f"Language {name} not found in AvailableLanguage enum.")
        return AvailableLanguage.EN.value
