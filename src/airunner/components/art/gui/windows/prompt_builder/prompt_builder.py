"""Madlibs-style Prompt Builder dialog.

This window lets the user assemble an image-generation prompt from curated
word lists (the classic AI Runner "Prompt Builder" concept) and produces a
prompt formatted for either Z-Image Turbo (6-part single prompt, no negative
prompt) or Stable Diffusion XL (layered prompt + negative "bug list").

* **Generate Prompt** writes the built prompt into the art generator form
  (the main prompt area) so the user can review or edit it.
* **Generate Image** does the same and immediately kicks off an image
  generation using the freshly written prompt.

No LLM is used anywhere in this flow.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Slot

from airunner.components.application.gui.windows.base_window import BaseWindow
from airunner.components.art.gui.windows.prompt_builder.prompt_builder_engine import (
    COLOR_PALETTES,
    COMPOSITIONS,
    LENSES,
    LIGHTING,
    QUALITY_TERMS,
    SCENE_LOCATIONS,
    SCENE_TIMES,
    SCENE_WEATHER,
    SHOT_TYPES,
    STYLES,
    SUBJECT_ACTIONS,
    SUBJECT_ATTRIBUTES,
    SUBJECT_NOUNS,
    SUBJECT_OBJECTS,
    PromptBuilderEngine,
    PromptBuilderState,
)
from airunner.components.art.gui.windows.prompt_builder.templates.prompt_builder_ui import (
    Ui_prompt_builder,
)
from airunner.enums import ImageGenerator, SignalCode


class PromptBuilder(BaseWindow):
    template_class_ = Ui_prompt_builder
    is_modal: bool = False
    title: str = "Prompt Builder"

    # Mapping of UI combo-box object name -> vocabulary list. Populated for
    # every slot the engine knows about.
    _COMBO_SOURCES: Dict[str, List[str]] = {
        "subject": SUBJECT_NOUNS,
        "action": SUBJECT_ACTIONS,
        "object": SUBJECT_OBJECTS,
        "scene": SCENE_LOCATIONS,
        "time_of_day": SCENE_TIMES,
        "weather": SCENE_WEATHER,
        "shot_type": SHOT_TYPES,
        "lens": LENSES,
        "composition": COMPOSITIONS,
        "lighting": LIGHTING,
        "quality": QUALITY_TERMS,
        "color_palette": COLOR_PALETTES,
    }
    _ATTRIBUTE_COMBOS: Dict[str, List[str]] = {
        name: options for name, options in SUBJECT_ATTRIBUTES.items()
    }

    def __init__(self, *args, **kwargs):
        self._engine = PromptBuilderEngine()
        self._last_state: PromptBuilderState = PromptBuilderState()
        self._preview_seed: int = 1
        self._generation_seed: int = 1
        super().__init__(*args, **kwargs)

    def initialize_window(self):
        """Populate all combo boxes and wire the signal handlers."""
        self._populate_combos()
        self._populate_style_group()
        self._set_default_generator()
        self._connect_signals()
        self._rebuild_preview()

    # -- setup --------------------------------------------------------------

    def _populate_combos(self) -> None:
        """Fill every static vocabulary combo box."""
        for name, options in self._COMBO_SOURCES.items():
            combo = getattr(self.ui, name, None)
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Random")
            combo.addItems(options)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        for name, options in self._ATTRIBUTE_COMBOS.items():
            combo = getattr(self.ui, f"attribute_{name}", None)
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Random")
            combo.addItems(options)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _populate_style_group(self) -> None:
        """Populate the style family + style detail combo boxes."""
        self.ui.style_group.blockSignals(True)
        self.ui.style_group.clear()
        self.ui.style_group.addItems(list(STYLES.keys()))
        self.ui.style_group.setCurrentText("Photorealistic")
        self.ui.style_group.blockSignals(False)
        self._populate_style_detail()

    def _populate_style_detail(self) -> None:
        """Refill the style-detail combo from the current style family."""
        group = self.ui.style_group.currentText() or "Photorealistic"
        options = STYLES.get(group, STYLES["Photorealistic"])
        self.ui.style_detail.blockSignals(True)
        self.ui.style_detail.clear()
        self.ui.style_detail.addItem("Random")
        self.ui.style_detail.addItems(options)
        self.ui.style_detail.setCurrentIndex(0)
        self.ui.style_detail.blockSignals(False)

    def _set_default_generator(self) -> None:
        """Default the target generator to the app's current model."""
        try:
            current = self.application_settings.current_image_generator
        except Exception:
            current = ImageGenerator.ZIMAGE.value
        target = (
            current
            if current in ("zimage", "stablediffusion")
            else ImageGenerator.ZIMAGE.value
        )
        self.ui.target_generator.blockSignals(True)
        self.ui.target_generator.setCurrentText(target)
        self.ui.target_generator.blockSignals(False)
        self._update_negative_visibility()

    def _connect_signals(self) -> None:
        """Wire all combo edits and buttons to a live preview rebuild."""
        for name in self._COMBO_SOURCES:
            combo = getattr(self.ui, name, None)
            if combo is not None:
                combo.currentIndexChanged.connect(self._on_combo_changed)
        for name in self._ATTRIBUTE_COMBOS:
            combo = getattr(self.ui, f"attribute_{name}", None)
            if combo is not None:
                combo.currentIndexChanged.connect(self._on_combo_changed)
        self.ui.style_group.currentIndexChanged.connect(
            self._on_style_group_changed
        )
        self.ui.style_detail.currentIndexChanged.connect(
            self._on_combo_changed
        )

        for name in (
            "custom_subject",
            "custom_scene",
            "custom_style",
            "custom_negative",
            "prefix",
            "suffix",
        ):
            widget = getattr(self.ui, name, None)
            if widget is not None:
                widget.textChanged.connect(self._on_text_changed)

        self.ui.randomize_checkbox.toggled.connect(self._on_randomize_toggled)
        self.ui.random_seed_checkbox.toggled.connect(
            self._on_random_seed_toggled
        )
        self.ui.seed_spinbox.valueChanged.connect(self._on_seed_changed)
        self.ui.target_generator.currentIndexChanged.connect(
            self._on_target_generator_changed
        )
        self.ui.randomize_button.clicked.connect(
            self._on_randomize_button_clicked
        )
        self.ui.generate_button.clicked.connect(self._on_generate_clicked)
        self.ui.generate_image_button.clicked.connect(
            self._on_generate_image_clicked
        )

    # -- state collection ---------------------------------------------------

    def _collect_state(self) -> PromptBuilderState:
        """Read every widget into a :class:`PromptBuilderState`.

        The seed is resolved from the UI: when "Random seed" is enabled the
        current working seed (``_preview_seed``, which advances after each
        generate) is used; otherwise the pinned spinbox value is used.
        """
        if self.ui.random_seed_checkbox.isChecked():
            seed = self._preview_seed
        else:
            seed = self.ui.seed_spinbox.value()
        state = PromptBuilderState(
            subject=self.ui.subject.currentText(),
            scene=self.ui.scene.currentText(),
            time_of_day=self.ui.time_of_day.currentText(),
            weather=self.ui.weather.currentText(),
            shot_type=self.ui.shot_type.currentText(),
            lens=self.ui.lens.currentText(),
            composition=self.ui.composition.currentText(),
            lighting=self.ui.lighting.currentText(),
            style_group=self.ui.style_group.currentText(),
            style_detail=self.ui.style_detail.currentText(),
            color_palette=self.ui.color_palette.currentText(),
            quality=self.ui.quality.currentText(),
            custom_subject=self.ui.custom_subject.text(),
            custom_scene=self.ui.custom_scene.text(),
            custom_style=self.ui.custom_style.text(),
            custom_negative=self.ui.custom_negative.text(),
            prefix=self.ui.prefix.text(),
            suffix=self.ui.suffix.text(),
            randomize=self.ui.randomize_checkbox.isChecked(),
            seed=seed,
            target_generator=self.ui.target_generator.currentText(),
        )
        for name in self._ATTRIBUTE_COMBOS:
            combo = getattr(self.ui, f"attribute_{name}", None)
            if combo is not None:
                state.attributes[name] = combo.currentText()
        return state

    # -- preview ------------------------------------------------------------

    def _rebuild_preview(self) -> None:
        """Regenerate the prompt from the current UI state and show it.

        The preview uses the current working seed so it doesn't flicker on
        every keystroke. Clicking **Randomize All** or **Generate** advances
        the seed so the next build differs. When "Random seed" is disabled,
        the pinned spinbox value is honored instead (resolved inside
        ``_collect_state``).
        """
        state = self._collect_state()
        result = self._engine.build(state)
        self._last_state = state
        self.ui.prompt_preview.setPlainText(result.prompt)
        self.ui.negative_prompt_preview.setPlainText(result.negative_prompt)
        self.ui.word_count_label.setText(
            f"{result.word_count} words ({len(result.prompt.split(','))} phrases)"
        )
        self._update_negative_visibility()

    def _update_negative_visibility(self) -> None:
        """Hide the negative-prompt section for generators without one."""
        is_sdxl = self.ui.target_generator.currentText() == "stablediffusion"
        self.ui.negative_prompt_label.setVisible(is_sdxl)
        self.ui.negative_prompt_preview.setVisible(is_sdxl)

    # -- signal handlers ----------------------------------------------------

    @Slot()
    def _on_combo_changed(self):
        self._rebuild_preview()

    @Slot()
    def _on_style_group_changed(self):
        self._populate_style_detail()
        self._rebuild_preview()

    @Slot(str)
    def _on_text_changed(self, _text: str):
        self._rebuild_preview()

    @Slot(bool)
    def _on_randomize_toggled(self, _checked: bool):
        self._rebuild_preview()

    @Slot(bool)
    def _on_random_seed_toggled(self, _checked: bool):
        # Toggling the random-seed mode re-syncs the preview. The seed
        # spinbox only matters when random seed is disabled.
        self._rebuild_preview()

    @Slot(int)
    def _on_seed_changed(self, _value: int):
        self._preview_seed = _value
        self._rebuild_preview()

    @Slot()
    def _on_target_generator_changed(self):
        self._update_negative_visibility()
        self._rebuild_preview()

    @Slot()
    def _on_randomize_button_clicked(self):
        """Pick a fresh random value into every slot and advance the seed.

        This gives the user a visible "shuffle" — every combo moves to a
        concrete value (not the "Random" placeholder) so the preview shows a
        fully fleshed-out prompt, and the seed advances so the next generate
        differs.
        """
        import random as _random

        rng = _random.Random()
        for name in self._COMBO_SOURCES:
            combo = getattr(self.ui, name, None)
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.setCurrentIndex(rng.randrange(1, combo.count()))
            combo.blockSignals(False)
        for name in self._ATTRIBUTE_COMBOS:
            combo = getattr(self.ui, f"attribute_{name}", None)
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.setCurrentIndex(rng.randrange(1, combo.count()))
            combo.blockSignals(False)
        self.ui.style_group.blockSignals(True)
        self.ui.style_group.setCurrentIndex(
            rng.randrange(0, self.ui.style_group.count())
        )
        self.ui.style_group.blockSignals(False)
        self._populate_style_detail()
        self.ui.style_detail.blockSignals(True)
        self.ui.style_detail.setCurrentIndex(
            rng.randrange(1, self.ui.style_detail.count())
        )
        self.ui.style_detail.blockSignals(False)

        self._preview_seed = rng.randint(0, 2**31 - 1)
        self._rebuild_preview()

    @Slot()
    def _on_generate_clicked(self):
        """Build the prompt and push it into the art generator form."""
        self._push_prompt_to_generator()

    @Slot()
    def _on_generate_image_clicked(self):
        """Build the prompt, insert it, and immediately generate an image."""
        self._push_prompt_to_generator()
        # Trigger generation. The generator form reads the freshly updated
        # ``generator_settings`` when it builds the image request.
        self.emit_signal(SignalCode.SD_GENERATE_IMAGE_SIGNAL)

    def _push_prompt_to_generator(self) -> None:
        """Build the final prompt and write it into the generator settings.

        This is shared by "Generate Prompt" and "Generate Image". The
        ``GENERATOR_FORM_UPDATE_VALUES_SIGNAL`` asks the art generator form to
        refresh its text areas from the updated settings (mirroring what the
        services-side ``update_generator_form_values()`` helper does).

        The build uses the current working seed, then advances it so the next
        generate produces a different prompt (when "Random seed" is enabled).
        """
        import random as _random

        state = self._collect_state()
        result = self._engine.build(state)

        # Persist the built prompt to generator settings.
        self.update_generator_settings(
            prompt=result.prompt,
            negative_prompt=result.negative_prompt,
        )
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)

        if self.ui.random_seed_checkbox.isChecked():
            self._preview_seed = _random.randint(0, 2**31 - 1)
            self.ui.seed_spinbox.blockSignals(True)
            self.ui.seed_spinbox.setValue(self._preview_seed)
            self.ui.seed_spinbox.blockSignals(False)
        self._rebuild_preview()
