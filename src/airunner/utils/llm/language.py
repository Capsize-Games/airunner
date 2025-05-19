from lingua import Language, LanguageDetectorBuilder
from airunner.enums import AvailableLanguage


def detect_language(txt: str) -> str:
    languages = [
        Language.ENGLISH,
        Language.FRENCH,
        Language.SPANISH,
        Language.KOREAN,
        Language.SPANISH,
        Language.CHINESE,
        Language.JAPANESE,
    ]
    detector = LanguageDetectorBuilder.from_languages(*languages).build()
    language = detector.detect_language_of(txt)
    if language is None:
        # Could not detect language, default to English
        return AvailableLanguage.EN
    name = language.iso_code_639_1.name
    if name == "JA":
        return AvailableLanguage.JP
    if name == "KO":
        return AvailableLanguage.KR
    try:
        return AvailableLanguage(name)
    except KeyError:
        print(f"Language {name} not found in AvailableLanguage enum.")
        return AvailableLanguage.EN
