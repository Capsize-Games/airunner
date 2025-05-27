"""
Unit tests for openvoice.api
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.api as api
from unittest.mock import patch, MagicMock
import numpy as np
import torch


def make_dummy_hps():
    class Dummy:
        pass

    hps = Dummy()
    hps.symbols = ["a", "b", "c"]
    hps.data = Dummy()
    hps.data.filter_length = 400
    hps.data.n_speakers = 1
    hps.data.sampling_rate = 16000
    hps.data.hop_length = 160
    hps.data.win_length = 400
    hps.data.text_cleaners = []
    hps.data.add_blank = False
    hps.speakers = {"spk": 0}
    hps.model = {}
    return hps


def test_module_importable():
    assert api is not None


def test_OpenVoiceBaseClass_load_ckpt():
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ):
        obj = api.OpenVoiceBaseClass("dummy_config", device="cpu")
        obj.model = MagicMock()
        obj.model.load_state_dict.return_value = ([], [])
        with patch("torch.load", return_value={"model": {}}):
            obj.load_ckpt("dummy_ckpt")


def test_OpenVoiceBaseClass_cuda_branch():
    with patch("torch.cuda.is_available", return_value=True), patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ):
        api.OpenVoiceBaseClass("dummy_config", device="cuda:0")


def test_BaseSpeakerTTS_get_text():
    hps = make_dummy_hps()
    result = api.BaseSpeakerTTS.get_text("abc", hps, is_symbol=True)
    assert isinstance(result, torch.LongTensor)


def test_BaseSpeakerTTS_get_text_add_blank():
    hps = make_dummy_hps()
    hps.data.add_blank = True
    with patch("airunner.vendor.openvoice.commons.intersperse", return_value=[1, 2, 3]):
        result = api.BaseSpeakerTTS.get_text("abc", hps, is_symbol=False)
        assert isinstance(result, torch.LongTensor)


def test_BaseSpeakerTTS_audio_numpy_concat():
    arrs = [np.ones(10, dtype=np.float32), np.ones(5, dtype=np.float32)]
    out = api.BaseSpeakerTTS.audio_numpy_concat(arrs, sr=16000, speed=1.0)
    assert isinstance(out, np.ndarray)


def test_BaseSpeakerTTS_split_sentences_into_pieces():
    with patch(
        "airunner.vendor.openvoice.utils.split_sentence", return_value=["a", "b"]
    ):
        out = api.BaseSpeakerTTS.split_sentences_into_pieces(
            "foo", api.AvailableLanguage.EN
        )
        assert out == ["a", "b"]


def test_BaseSpeakerTTS_tts_output_path():
    hps = make_dummy_hps()
    tts = api.BaseSpeakerTTS.__new__(api.BaseSpeakerTTS)
    tts.hps = hps
    tts.device = "cpu"
    tts.model = MagicMock()
    tts.get_text = MagicMock(return_value=torch.ones(3, dtype=torch.long))
    tts.split_sentences_into_pieces = MagicMock(return_value=["foo"])
    with patch("soundfile.write") as sf_write:
        with patch.object(tts.model, "infer", return_value=[torch.ones(1, 1, 3)]):
            tts.hps.speakers = {"spk": 0}
            tts.tts("foo", "dummy.wav", "spk")
            sf_write.assert_called_once()


def test_BaseSpeakerTTS_tts_output_path_real(tmp_path):
    hps = make_dummy_hps()
    tts = api.BaseSpeakerTTS.__new__(api.BaseSpeakerTTS)
    tts.hps = hps
    tts.device = "cpu"
    tts.model = MagicMock()
    tts.get_text = MagicMock(return_value=torch.ones(3, dtype=torch.long))
    tts.split_sentences_into_pieces = MagicMock(return_value=["foo"])
    tts.hps.speakers = {"spk": 0}
    with patch.object(tts.model, "infer", return_value=[torch.ones(1, 1, 3)]):
        output_path = tmp_path / "out.wav"
        tts.tts("foo", str(output_path), "spk")
        assert output_path.exists()


def test_ToneColorConverter_init_no_watermark():
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ):
        obj = api.ToneColorConverter(
            "dummy_config", device="cpu", enable_watermark=False
        )
        assert obj.watermark_model is None


def test_ToneColorConverter_import_wavmark(monkeypatch):
    class DummyWavmark:
        @staticmethod
        def load_model():
            class DummyModel:
                def to(self, device):
                    return self

            return DummyModel()

    import sys

    sys.modules["wavmark"] = DummyWavmark
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ):
        obj = api.ToneColorConverter(
            "dummy_config", device="cpu", enable_watermark=True
        )
        assert obj.watermark_model is not None


def test_ToneColorConverter_extract_se_and_convert():
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ), patch(
        "librosa.load", return_value=(np.ones(16000), 16000)
    ), patch(
        "airunner.vendor.openvoice.mel_processing.spectrogram_torch",
        return_value=torch.ones(1, 201, 10),
    ), patch(
        "torch.save"
    ), patch(
        "soundfile.write"
    ), patch.object(
        api.ToneColorConverter, "add_watermark", return_value=np.ones(32000)
    ):
        obj = api.ToneColorConverter("dummy_config", device="cpu")
        # Attach required model methods
        model_mock = MagicMock()
        model_mock.ref_enc.return_value = torch.ones(1, 10)
        # Return correct shape for voice_conversion
        model_mock.voice_conversion.return_value = torch.ones(1, 1, 16000)
        obj.model = model_mock
        obj.hps = make_dummy_hps()
        obj.device = "cpu"
        # extract_se
        gs = obj.extract_se(["dummy.wav"])
        assert isinstance(gs, torch.Tensor)
        # convert
        out = obj.convert(
            "dummy.wav", torch.ones(1, 10, 1), torch.ones(1, 10, 1), output_path=None
        )
        assert isinstance(out, np.ndarray)


def test_ToneColorConverter_extract_se_with_save():
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ), patch(
        "librosa.load", return_value=(np.ones(16000), 16000)
    ), patch(
        "airunner.vendor.openvoice.mel_processing.spectrogram_torch",
        return_value=torch.ones(1, 201, 10),
    ), patch(
        "torch.save"
    ) as tsave:
        obj = api.ToneColorConverter("dummy_config", device="cpu")
        obj.model = MagicMock()
        obj.model.ref_enc.return_value = torch.ones(1, 10)
        obj.hps = make_dummy_hps()
        obj.device = "cpu"
        gs = obj.extract_se(["dummy.wav"], se_save_path="/tmp/dummy.pt")
        tsave.assert_called_once()
        assert isinstance(gs, torch.Tensor)


def test_ToneColorConverter_convert_output_path():
    with patch(
        "airunner.vendor.openvoice.utils.get_hparams_from_file",
        return_value=make_dummy_hps(),
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.__init__", return_value=None
    ), patch(
        "airunner.vendor.openvoice.models.SynthesizerTrn.to", return_value=MagicMock()
    ), patch(
        "librosa.load", return_value=(np.ones(16000), 16000)
    ), patch(
        "airunner.vendor.openvoice.mel_processing.spectrogram_torch",
        return_value=torch.ones(1, 201, 10),
    ), patch(
        "soundfile.write"
    ) as sf_write:
        obj = api.ToneColorConverter("dummy_config", device="cpu")
        obj.model = MagicMock()
        obj.model.voice_conversion.return_value = torch.ones(1, 1, 16000)
        obj.hps = make_dummy_hps()
        obj.device = "cpu"
        obj.add_watermark = MagicMock(return_value=np.ones(32000))
        out = obj.convert(
            "dummy.wav",
            torch.ones(1, 10, 1),
            torch.ones(1, 10, 1),
            output_path="dummy.wav",
        )
        sf_write.assert_called_once()
        assert out is None


def test_ToneColorConverter_add_watermark_none():
    obj = api.ToneColorConverter.__new__(api.ToneColorConverter)
    obj.watermark_model = None
    audio = np.ones(32000, dtype=np.float32)
    out = obj.add_watermark(audio.copy(), "msg")
    assert np.allclose(out, audio)


def test_ToneColorConverter_add_watermark_audio_too_short():
    obj = api.ToneColorConverter.__new__(api.ToneColorConverter)
    obj.watermark_model = MagicMock()
    obj.device = "cpu"
    audio = np.ones(1000, dtype=np.float32)  # Too short for watermark
    with patch(
        "airunner.vendor.openvoice.utils.string_to_bits",
        return_value=np.ones(32, dtype=np.int8),
    ):
        out = obj.add_watermark(audio.copy(), "msg")
        assert np.allclose(out, audio)


def test_ToneColorConverter_detect_watermark_audio_too_short():
    obj = api.ToneColorConverter.__new__(api.ToneColorConverter)
    obj.watermark_model = MagicMock()
    obj.device = "cpu"
    audio = np.ones(1000, dtype=np.float32)  # Too short for detection
    msg = obj.detect_watermark(audio, n_repeat=1)
    assert msg == "Fail"


def test_ToneColorConverter_add_and_detect_watermark():
    obj = api.ToneColorConverter.__new__(api.ToneColorConverter)
    obj.watermark_model = MagicMock()
    obj.device = "cpu"
    audio = np.ones(32000, dtype=np.float32)
    # Provide enough bits for n_repeat=1
    with patch(
        "airunner.vendor.openvoice.utils.string_to_bits",
        return_value=np.ones(32, dtype=np.int8),
    ):
        obj.watermark_model.encode.return_value = torch.ones(16000)
        out = obj.add_watermark(audio.copy(), "msg")
        assert isinstance(out, np.ndarray)
    obj.watermark_model.decode.return_value = torch.ones(32)
    msg = obj.detect_watermark(audio, n_repeat=1)
    assert isinstance(msg, str)
