import pytest
from unittest.mock import patch, MagicMock, call
from airunner.gui.windows.filter_window import FilterWindow


@pytest.fixture
def mock_image_filter():
    # Mock the ImageFilter and its related values
    mock_filter = MagicMock()
    mock_filter.name = "pixel_art"
    mock_filter.display_name = "Pixel Art"
    mock_filter.filter_class = "PixelFilter"
    mock_value = MagicMock()
    mock_value.id = 1
    mock_value.name = "number_of_colors"
    mock_value.value = "24"
    mock_value.value_type = "int"
    mock_value.min_value = 2
    mock_value.max_value = 1024
    mock_filter.image_filter_values = [mock_value]
    return mock_filter


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_filter_window_init(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    # Patch the objects.get method to return our mock filter
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    # Patch QTimer to avoid side effects
    with patch("airunner.gui.windows.filter_window.QTimer") as mock_timer:
        # Patch exec to avoid launching the dialog
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            assert fw.image_filter_model_name == "pixel_art"
            assert fw.window_title == "Pixel Art"
            assert len(fw._filter_values) == 1
            fv = fw._filter_values[0]
            assert fv.name == "number_of_colors"
            assert fv.value == "24"
            assert fv.value_type == "int"
            assert fv.min_value == 2
            assert fv.max_value == 1024
            # Test save() actually calls the ORM update
            with patch(
                "airunner.gui.windows.filter_window.ImageFilterValue.objects.update"
            ) as mock_update:
                fv.value = "42"
                fv.save()
                mock_update.assert_called_once_with(1, value="42")


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_show_event_and_preview(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    with patch("airunner.gui.windows.filter_window.QTimer") as mock_timer:
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.ui = MagicMock()
            fw.ui.content.layout.return_value = MagicMock()
            with patch(
                "airunner.gui.windows.filter_window.FilterSliderWidget"
            ) as mock_slider:
                mock_slider_inst = MagicMock()
                mock_slider.return_value = mock_slider_inst
                fw.preview_filter = MagicMock()
                fw.setWindowTitle = MagicMock()
                fw.showEvent(MagicMock())
                fw.setWindowTitle.assert_called_once_with("Pixel Art")
                fw.preview_filter.assert_called_once()
                fw.ui.content.layout.return_value.addWidget.assert_called_once_with(
                    mock_slider_inst
                )


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_key_press_event(mock_base_init, mock_ImageFilter, mock_image_filter):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.reject = MagicMock()
            event = MagicMock()
            event.key.return_value = 16777216
            fw.keyPressEvent(event)
            fw.reject.assert_called_once()


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_filter_object(mock_base_init, mock_ImageFilter, mock_image_filter):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.image_filter.filter_class = "PixelFilter"
            fw.image_filter.name = "pixel_art"
            fw.image_filter.image_filter_values = (
                mock_image_filter.image_filter_values
            )
            with patch(
                "airunner.gui.windows.filter_window.session_scope"
            ) as mock_scope:
                mock_scope.return_value.__enter__.return_value = MagicMock()
                with patch("importlib.import_module") as mock_import:
                    mock_class = MagicMock()
                    mock_import.return_value = MagicMock(
                        PixelFilter=mock_class
                    )
                    fw.image_filter.filter_class = "PixelFilter"
                    fw.image_filter.name = "pixel_art"
                    fw._filter = None
                    result = fw.filter_object()
                    assert result == mock_class()


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_accept_and_reject_and_preview_filter(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.api = MagicMock()
            fw.api.art.image_filter.cancel = MagicMock()
            fw.api.art.image_filter.apply = MagicMock()
            fw.api.art.image_filter.preview = MagicMock()
            fw.filter_object = MagicMock(return_value="obj")
            # test reject
            with patch(
                "airunner.gui.windows.base_window.BaseWindow.reject"
            ) as base_reject:
                fw.reject()
                fw.api.art.image_filter.cancel.assert_called_once()
                base_reject.assert_called_once()
            # test accept
            with patch(
                "airunner.gui.windows.base_window.BaseWindow.accept"
            ) as base_accept:
                fw.accept()
                fw.api.art.image_filter.apply.assert_called_once_with("obj")
                base_accept.assert_called_once()
            # test preview_filter
            fw._debounce_timer = MagicMock()
            fw._debounce_timer.stop = MagicMock()
            fw._debounce_timer.start = MagicMock()
            fw.preview_filter()
            fw._debounce_timer.stop.assert_called_once()
            fw._debounce_timer.start.assert_called_once()
            # test _do_preview_filter
            fw._do_preview_filter()
            fw.api.art.image_filter.preview.assert_called_with("obj")


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_show_event_else_branches(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    # Test showEvent with value_type not in ("float", "int") and value != "float"
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    # Add a value_type that is not float or int
    mock_value = MagicMock()
    mock_value.id = 2
    mock_value.name = "mode"
    mock_value.value = "L"
    mock_value.value_type = "str"
    mock_value.min_value = None
    mock_value.max_value = None
    mock_image_filter.image_filter_values.append(mock_value)
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.ui = MagicMock()
            fw.ui.content.layout.return_value = MagicMock()
            with patch(
                "airunner.gui.windows.filter_window.FilterSliderWidget"
            ) as mock_slider:
                mock_slider_inst = MagicMock()
                mock_slider.return_value = mock_slider_inst
                fw.preview_filter = MagicMock()
                fw.setWindowTitle = MagicMock()
                # Should not add a widget for the str value_type
                fw.showEvent(MagicMock())
                # Only one widget for the int value_type
                fw.ui.content.layout.return_value.addWidget.assert_called_once_with(
                    mock_slider_inst
                )


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_filter_object_bool_branch(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    # Add a bool value_type
    mock_value = MagicMock()
    mock_value.id = 3
    mock_value.name = "enabled"
    mock_value.value = "True"
    mock_value.value_type = "bool"
    mock_value.min_value = None
    mock_value.max_value = None
    mock_image_filter.image_filter_values.append(mock_value)
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.image_filter.filter_class = "PixelFilter"
            fw.image_filter.name = "pixel_art"
            fw.image_filter.image_filter_values = (
                mock_image_filter.image_filter_values
            )
            with patch(
                "airunner.gui.windows.filter_window.session_scope"
            ) as mock_scope:
                mock_scope.return_value.__enter__.return_value = MagicMock()
                with patch("importlib.import_module") as mock_import:
                    mock_class = MagicMock()
                    mock_import.return_value = MagicMock(
                        PixelFilter=mock_class
                    )
                    fw.image_filter.filter_class = "PixelFilter"
                    fw.image_filter.name = "pixel_art"
                    fw._filter = None
                    result = fw.filter_object()
                    assert result == mock_class()


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_accept_and_reject_super_calls(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.api = MagicMock()
            fw.api.art.image_filter.cancel = MagicMock()
            fw.api.art.image_filter.apply = MagicMock()
            fw.filter_object = MagicMock(return_value="obj")
            # test super().reject()
            with patch(
                "airunner.gui.windows.base_window.BaseWindow.reject"
            ) as base_reject:
                fw.reject()
                base_reject.assert_called_once()
            # test super().accept()
            with patch(
                "airunner.gui.windows.base_window.BaseWindow.accept"
            ) as base_accept:
                fw.accept()
                base_accept.assert_called_once()


@patch("airunner.gui.windows.filter_window.ImageFilter")
@patch(
    "airunner.gui.windows.filter_window.BaseWindow.__init__", return_value=None
)
def test_show_event_invalid_float_value_raises(
    mock_base_init, mock_ImageFilter, mock_image_filter
):
    mock_ImageFilter.objects.get.return_value = mock_image_filter
    # value_type float, value is an invalid float string
    mock_value = MagicMock()
    mock_value.id = 6
    mock_value.name = "bad_float"
    mock_value.value = "not_a_float"
    mock_value.value_type = "float"
    mock_value.min_value = 1
    mock_value.max_value = 10
    mock_image_filter.image_filter_values = [mock_value]
    with patch("airunner.gui.windows.filter_window.QTimer"):
        with patch.object(FilterWindow, "exec", return_value=None):
            fw = FilterWindow(image_filter_id=123)
            fw.ui = MagicMock()
            fw.ui.content.layout.return_value = MagicMock()
            with patch(
                "airunner.gui.windows.filter_window.FilterSliderWidget"
            ):
                fw.preview_filter = MagicMock()
                fw.setWindowTitle = MagicMock()
                with pytest.raises(ValueError):
                    fw.showEvent(MagicMock())
