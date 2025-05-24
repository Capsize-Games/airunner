import pytest
from unittest.mock import MagicMock
from airunner.api.art_services import ARTAPIService
from airunner.enums import SignalCode, GeneratorSection
from airunner.handlers.stablediffusion.image_request import ImageRequest


@pytest.fixture
def art_service():
    emitted = []

    def emit_signal(code, data=None):
        emitted.append((code, data))

    service = ARTAPIService(emit_signal=emit_signal)
    service._emitted = emitted
    return service


def test_update_batch_images(art_service):
    art_service.update_batch_images(["img1", "img2"])
    assert (
        art_service._emitted[-1][0] == SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL
    )
    assert art_service._emitted[-1][1]["images"] == ["img1", "img2"]


def test_save_prompt(art_service):
    art_service.save_prompt("p", "n", "sp", "sn")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_SAVE_PROMPT_SIGNAL
    assert data["prompt"] == "p"
    assert data["negative_prompt"] == "n"
    assert data["secondary_prompt"] == "sp"
    assert data["secondary_negative_prompt"] == "sn"


def test_load(art_service):
    art_service.load("prompt1")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_LOAD_PROMPT_SIGNAL
    assert data["saved_prompt"] == "prompt1"
    art_service.load()
    code, data = art_service._emitted[-1]
    assert data["saved_prompt"] is None


def test_unload(art_service):
    art_service.unload()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_UNLOAD_SIGNAL
    assert data is None


def test_model_changed(art_service):
    art_service.model_changed("m", "v", "p")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_ART_MODEL_CHANGED
    assert data == {"model": "m", "version": "v", "pipeline": "p"}
    art_service.model_changed(None, None, None)
    code, data = art_service._emitted[-1]
    assert data == {}


def test_load_safety_checker(art_service):
    art_service.load_safety_checker()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SAFETY_CHECKER_LOAD_SIGNAL
    assert data is None


def test_unload_safety_checker(art_service):
    art_service.unload_safety_checker()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL
    assert data is None


def test_change_scheduler(art_service):
    art_service.change_scheduler("ddim")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.CHANGE_SCHEDULER_SIGNAL
    assert data["scheduler"] == "ddim"


def test_lora_updated(art_service):
    art_service.lora_updated()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.LORA_UPDATED_SIGNAL
    assert data == {}


def test_embedding_updated(art_service):
    art_service.embedding_updated()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.EMBEDDING_UPDATED_SIGNAL
    assert data == {}


def test_final_progress_update(art_service):
    art_service.final_progress_update(5)
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_PROGRESS_SIGNAL
    assert data["step"] == 5 and data["total"] == 5


def test_progress_update(art_service):
    art_service.progress_update(2, 10)
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_PROGRESS_SIGNAL
    assert data["step"] == 2 and data["total"] == 10


def test_pipeline_loaded(art_service):
    art_service.pipeline_loaded(GeneratorSection.TXT2IMG)
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_PIPELINE_LOADED_SIGNAL
    assert data["generator_section"] == GeneratorSection.TXT2IMG


def test_generate_image_signal(art_service):
    art_service.generate_image_signal()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.SD_GENERATE_IMAGE_SIGNAL
    assert data is None


def test_llm_image_generated(art_service):
    art_service.llm_image_generated(
        "p", "sp", GeneratorSection.TXT2IMG, 512, 512
    )
    code, data = art_service._emitted[-1]
    assert code == SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL
    msg = data["message"]
    assert msg["prompt"] == "p"
    assert msg["second_prompt"] == "sp"
    assert msg["type"] == GeneratorSection.TXT2IMG
    assert msg["width"] == 512
    assert msg["height"] == 512


def test_stop_progress_bar(art_service):
    art_service.stop_progress_bar()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL
    assert data is None


def test_clear_progress_bar(art_service):
    art_service.clear_progress_bar()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL
    assert data == {"do_clear": True}


def test_missing_required_models(art_service):
    art_service.missing_required_models("fail")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.MISSING_REQUIRED_MODELS
    assert data["title"] == "Model Not Found"
    assert data["message"] == "fail"


def test_send_request(art_service):
    req = ImageRequest()
    art_service.send_request(req, {"foo": "bar"})
    code, data = art_service._emitted[-1]
    assert code == SignalCode.DO_GENERATE_SIGNAL
    assert data["foo"] == "bar"
    assert isinstance(data["image_request"], ImageRequest)
    art_service.send_request()
    code, data = art_service._emitted[-1]
    assert isinstance(data["image_request"], ImageRequest)


def test_interrupt_generate(art_service):
    art_service.interrupt_generate()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL
    assert data is None


def test_active_grid_area_updated(art_service):
    art_service.active_grid_area_updated()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED
    assert data is None


def test_update_generator_form_values(art_service):
    art_service.update_generator_form_values()
    code, data = art_service._emitted[-1]
    assert code == SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL
    assert data is None


def test_toggle_sd(art_service):
    art_service.toggle_sd(True, "cb", "fin")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.TOGGLE_SD_SIGNAL
    assert data["enabled"] is True
    assert data["callback"] == "cb"
    assert data["finalize"] == "fin"


def test_load_non_sd(art_service):
    art_service.load_non_sd("cb")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.LOAD_NON_SD_MODELS
    assert data["callback"] == "cb"


def test_unload_non_sd(art_service):
    art_service.unload_non_sd("cb")
    code, data = art_service._emitted[-1]
    assert code == SignalCode.UNLOAD_NON_SD_MODELS
    assert data["callback"] == "cb"
