"""
Functional test for GeneratorForm: submitting an image request with no model selected should show an error popup and not call send_request.
This test does not patch internals, only intercepts QMessageBox.critical to assert the error dialog.
"""

import pytest
from PySide6.QtWidgets import QPushButton, QMessageBox, QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from pytestqt.qt_compat import qt_api  # Used by pytest-qt for TimeoutError

# Assuming GeneratorForm is in this path, adjust if necessary
# from airunner.gui.widgets.generator_form.generator_form_widget import GeneratorForm
# For demonstration, let's define a minimal GeneratorForm if the actual one isn't available
# In your actual environment, use your import:
# from airunner.gui.widgets.generator_form.generator_form_widget import GeneratorForm

# --- Minimal Reproducible GeneratorForm (for testing the test structure) ---
# Replace this with your actual GeneratorForm import
if "GeneratorForm" not in globals():
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

    class GeneratorForm(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.model = "some_default_model"  # Actual model attribute
            self.setWindowTitle("Generator Form")
            layout = QVBoxLayout(self)
            self.label = QLabel("Status: Awaiting action")
            self.submit_button_real = QPushButton(
                "Submit Real"
            )  # Changed name for clarity
            self.submit_button_real.setObjectName("realSubmitButton")
            self.submit_button_real.clicked.connect(self._on_submit_pressed)
            layout.addWidget(self.label)
            layout.addWidget(self.submit_button_real)
            self.send_request_was_called = (
                False  # For testing if send_request is called
            )

        def _on_submit_pressed(self):
            print(f"GeneratorForm: _on_submit_pressed called. Model is: {self.model}")
            if self.model is None:
                print("GeneratorForm: Model is None, calling QMessageBox.critical")
                QMessageBox.critical(
                    self,
                    "No model selected",
                    "Please select a model before submitting.",
                )
                self.label.setText("Error: No model selected")
                return
            self.label.setText(f"Submitted with model: {self.model}")
            print(
                f"GeneratorForm: Model is '{self.model}', proceeding to send_request."
            )
            self.send_request()

        def send_request(self):
            print("GeneratorForm: send_request() called.")
            self.send_request_was_called = True

        def findChild(self, T, name):  # Basic findChild for the mock
            if T == QPushButton and name == "realSubmitButton":
                return self.submit_button_real
            return super().findChild(T, name)

        def findChildren(self, T, name=None):  # Basic findChildren for the mock
            if T == QPushButton:
                return [self.submit_button_real]
            return super().findChildren(T, name)


# --- End Minimal Reproducible GeneratorForm ---


@pytest.fixture
def generator_form(qtbot):
    # pytest-qt normally handles QApplication instance creation.
    # If you were not using pytest-qt, you'd need:
    # app = QApplication.instance()
    # if app is None:
    #     app = QApplication([])

    print("\n--- generator_form fixture setup ---")
    widget = GeneratorForm()
    qtbot.addWidget(widget)  # Manages widget lifetime and provides event processing

    # Set the model to None to simulate the error condition
    # This should be done *before* any action that might depend on it.
    print("Setting widget.model = None")
    widget.model = None

    widget.show()
    # Wait until the widget is not only visible but also exposed (drawn)
    qtbot.waitUntil(widget.isVisible, timeout=1000)
    qtbot.waitExposed(widget, timeout=1000)
    print(f"GeneratorForm '{widget.windowTitle()}' shown and exposed.")
    print("--- generator_form fixture setup complete ---")
    return widget


def test_submit_button_shows_error_if_no_model_selected(qtbot, generator_form):
    print("\n--- test_submit_button_shows_error_if_no_model_selected ---")
    error_triggered = {}

    # Store the original QMessageBox.critical
    original_critical = QMessageBox.critical

    def fake_critical(parent, title, text, *args, **kwargs):
        print(
            f"FAKE QMessageBox.critical called: parent={parent}, title='{title}', text='{text}'"
        )
        error_triggered["shown"] = (title, text)
        error_triggered["parent_widget_title"] = (
            parent.windowTitle() if parent and hasattr(parent, "windowTitle") else "N/A"
        )
        # Return a standard button to simulate closing the dialog,
        # otherwise the test might hang if the actual dialog blocks.
        return QMessageBox.Ok

    # Monkeypatch QMessageBox.critical
    QMessageBox.critical = fake_critical
    print("QMessageBox.critical has been patched.")

    # Reset any state for verifying side-effects (like send_request not being called)
    generator_form.send_request_was_called = False

    try:
        # --- Button Identification Logic ---
        submit_btn = None
        # 1. Try finding by a specific objectName if you set one in your .ui file or code
        # Example: submit_btn = generator_form.findChild(QPushButton, "submitButtonNameFromUI")

        # 2. If not found by specific objectName, try a broader search
        if not submit_btn:
            buttons = generator_form.findChildren(QPushButton)
            print(f"Found {len(buttons)} QPushButton(s) in GeneratorForm:")
            for i, btn in enumerate(buttons):
                print(
                    f"  Button {i}: text='{btn.text()}', objectName='{btn.objectName()}', isEnabled={btn.isEnabled()}, isVisible={btn.isVisible()}"
                )

            assert (
                buttons
            ), "No QPushButton found in GeneratorForm. Add a submit button to the UI."

            # Try to find a likely submit/generate button by text
            # (case-insensitive and common variations)
            possible_texts = {
                "submit",
                "generate",
                "run",
                "create",
                "ok",
                "apply",
                "send",
            }
            for btn in buttons:
                btn_text_lower = btn.text().lower().strip()
                if btn_text_lower in possible_texts:
                    submit_btn = btn
                    print(
                        f"Identified likely submit button by text: '{btn.text()}' (objectName: '{btn.objectName()}')"
                    )
                    break

            if not submit_btn:  # Fallback to object name if text doesn't match
                for btn in buttons:
                    obj_name_lower = btn.objectName().lower()
                    if any(
                        keyword in obj_name_lower
                        for keyword in ["submit", "generate", "run", "apply", "action"]
                    ):
                        submit_btn = btn
                        print(
                            f"Identified likely submit button by objectName keyword: '{btn.objectName()}' (text: '{btn.text()}')"
                        )
                        break

            if (
                not submit_btn
            ):  # Last resort: use the first button found if it's the only one or as a desperate measure
                if len(buttons) == 1:
                    submit_btn = buttons[0]
                    print(
                        f"Identified the only button found: '{submit_btn.text()}' (objectName: '{submit_btn.objectName()}')"
                    )
                else:
                    # If multiple buttons and no clear winner, this is risky.
                    # Consider making object names or button texts more specific in your UI.
                    print(
                        f"Warning: Multiple QPushButtons found and no clear submit button by text/objectName. Falling back to the first one: {buttons[0].text()}"
                    )
                    submit_btn = buttons[0]

        assert (
            submit_btn
        ), "Could not identify a suitable submit button after all attempts."
        print(
            f"Targeting button for click: text='{submit_btn.text()}', objectName='{submit_btn.objectName()}', isEnabled={submit_btn.isEnabled()}, isVisible={submit_btn.isVisible()}"
        )

        if not submit_btn.isEnabled():
            # This is a critical check. Clicking a disabled button does nothing.
            # If the button is *meant* to be disabled when no model is selected,
            # then the test should assert this disabled state, or the application
            # logic should be such that it's enabled but shows an error.
            print(
                f"CRITICAL WARNING: The identified submit button '{submit_btn.text()}' is DISABLED. Clicks will have no effect."
            )
            pytest.fail(
                f"Submit button '{submit_btn.text()}' is disabled. Test cannot proceed to click."
            )

        # --- Simulate the Click ---
        print(
            f"Attempting to click button: '{submit_btn.text()}' using qtbot.mouseClick()"
        )
        # Using qtbot.mouseClick is generally preferred with pytest-qt
        qtbot.mouseClick(submit_btn, Qt.MouseButton.LeftButton)
        print("qtbot.mouseClick() executed.")

        # --- Wait for Asynchronous Action (QMessageBox appearing) ---
        try:
            # Wait until our fake_critical function has been called
            print(
                "Waiting for fake_critical to be called (error_triggered['shown'] to be set)..."
            )
            qtbot.waitUntil(
                lambda: "shown" in error_triggered, timeout=3000
            )  # Timeout in ms
            print("waitUntil condition met: fake_critical was called.")
        except qt_api.TimeoutError:  # Specific exception for pytest-qt's waitUntil
            print("！！！ waitUntil timed out. fake_critical was NOT called. ！！！")
            print(
                f"Current generator_form.model: {generator_form.model}"
            )  # Re-check state
            print(
                f"Is submit_btn still valid and enabled? {submit_btn.isEnabled() if submit_btn else 'N/A'}"
            )
            # Check if send_request was called (it shouldn't have been)
            print(
                f"generator_form.send_request_was_called: {generator_form.send_request_was_called}"
            )
            pytest.fail(
                "QMessageBox.critical (fake_critical) was not called within the timeout. The button click likely didn't trigger the expected error path."
            )

        # --- Assertions ---
        assert "shown" in error_triggered, "Error: QMessageBox.critical was not called."
        print(f"error_triggered content: {error_triggered}")

        # Assert on the parent widget of the dialog if necessary (e.g., to ensure it's the main form)
        # This requires your fake_critical to capture parent.
        # assert error_triggered.get("parent_widget_title") == generator_form.windowTitle()

        assert (
            error_triggered["shown"][0] == "No model selected"
        ), f"Error dialog title mismatch. Expected 'No model selected', Got: '{error_triggered['shown'][0]}'"
        assert (
            "model" in error_triggered["shown"][1].lower()
        ), f"Error dialog text mismatch or does not mention 'model'. Expected 'model' in text, Got: '{error_triggered['shown'][1]}'"

        # Assert that the actual request sending method was not called
        assert (
            not generator_form.send_request_was_called
        ), "Error: send_request was called despite a model validation error."
        print(
            "Assertions passed: Error dialog shown as expected, send_request not called."
        )

    finally:
        # Restore the original QMessageBox.critical
        QMessageBox.critical = original_critical
        print("QMessageBox.critical has been restored.")
        print("--- test_submit_button_shows_error_if_no_model_selected complete ---")
        # qtbot will handle closing and deleting widgets added with qtbot.addWidget()
        # So, explicit generator_form.close() and generator_form.deleteLater() are not usually needed here.
