from PySide6.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Slot

from airunner.components.downloader.gui.windows.setup_wizard.base_wizard import (
    BaseWizard,
)
from airunner.components.downloader.gui.windows.setup_wizard.installation_settings.templates.choose_models_ui import (
    QSizePolicy,
    QSpacerItem,
    Ui_install_success_page,
)
from airunner.components.art.data.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner.components.data.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)


class ChooseModelsPage(BaseWizard):
    class_name_ = Ui_install_success_page

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models_enabled = {
            "stable_diffusion": True,
            "speecht5": True,
            "whisper": True,
            "mistral": True,
            "embedding_model": True,
            "openvoice_model": True,
        }

        # Prepare core items (safety checker, feature extractor) and per-version controlnet groups
        core_items = [
            {
                "name": "safety_checker",
                "display_name": "Safety Checker",
                "size": 1.2 * 1024 * 1024,
            },
            {
                "name": "feature_extractor",
                "display_name": "Feature Extractor",
                "size": 1.7 * 1024 * 1024,
            },
        ]

        # Prepare core items (these will be placed outside the scroll area in the main grid)
        self._core_widgets = []
        for item in core_items:
            chk = QCheckBox(self)
            chk.setText(item["display_name"])
            chk.setChecked(True)
            chk.setObjectName(item["name"])
            self.models_enabled[item["name"]] = True
            # Wire toggles to dedicated slots when appropriate
            if item["name"] == "safety_checker":
                chk.toggled.connect(
                    lambda v, n="safety_checker": self._core_toggled(n, v)
                )
            elif item["name"] == "feature_extractor":
                chk.toggled.connect(
                    lambda v, n="feature_extractor": self._core_toggled(n, v)
                )
            self._core_widgets.append((item["name"], chk))

        # Group ControlNet models by version
        # Expose the stable-diffusion model bootstrap list for the installer
        self.models = model_bootstrap_data

        from collections import defaultdict

        version_map = defaultdict(list)
        for item in controlnet_bootstrap_data:
            version_map[item["version"]].append(item)

        # Make the groupBox act as a checkable 'Stable Diffusion' group
        try:
            self.ui.groupBox.setTitle("Stable Diffusion")
            self.ui.groupBox.setCheckable(True)
            self.ui.groupBox.setChecked(True)
            try:
                self.ui.groupBox.toggled.connect(self.stable_diffusion_toggled)
            except Exception:
                pass

            # Create a top-level scroll area inside the Stable Diffusion group to hold all version groups
            top_scroll = QScrollArea(self)
            top_scroll.setWidgetResizable(True)
            top_inner = QWidget()
            top_inner_layout = QVBoxLayout(top_inner)
            top_inner.setLayout(top_inner_layout)
            top_scroll.setWidget(top_inner)
            # add the top scroll area into the existing stable_diffusion_layout
            try:
                self.ui.stable_diffusion_layout.layout().addWidget(top_scroll)
            except Exception:
                # fallback: ignore if layout not present
                pass
        except Exception:
            pass

        # For each version, create a header with "Core files" and "Controlnet" checkboxes and a scroll area for models
        for version in sorted(version_map.keys()):
            # Section header (group box)
            from PySide6.QtWidgets import QGroupBox, QLabel, QHBoxLayout

            # Create a version group and a master checkbox that controls the whole section
            version_group = QGroupBox(self)
            v_layout = QVBoxLayout(version_group)

            # Create a checkable group box for the SD version (acts as the SD 1.5 / SDXL 1.0 checkbox)
            master_flag = f"sd_{version}"
            self.models_enabled[master_flag] = True
            version_group.setTitle(version)
            version_group.setCheckable(True)
            version_group.setChecked(True)

            # Core files checkbox (on its own row)
            core_chk = QCheckBox("Core files", self)
            core_flag = f"core_{version}"
            self.models_enabled[core_flag] = True
            core_chk.setChecked(True)
            core_chk.toggled.connect(
                lambda val, flag=core_flag: self._core_version_toggled(
                    flag, val
                )
            )
            v_layout.addWidget(core_chk)

            # Controlnet group (checkable) containing a plain container for models (no inner scrollarea)
            controlnet_flag = f"controlnet_{version}"
            self.models_enabled[controlnet_flag] = True
            controlnet_group = QGroupBox("Controlnet", self)
            controlnet_group.setCheckable(True)
            controlnet_group.setChecked(True)
            controlnet_layout = QVBoxLayout(controlnet_group)

            # Simple widget container for model checkboxes (no per-version scroll area)
            models_container = QWidget()
            models_layout = QVBoxLayout(models_container)
            models_container.setLayout(models_layout)
            controlnet_layout.addWidget(models_container)
            v_layout.addWidget(controlnet_group)

            # local models list for this version (used by handlers)
            models = version_map[version]

            # Populate model checkboxes
            for item in models:
                cb = QCheckBox(item["display_name"], self)
                cb.setChecked(True)
                cb.setObjectName(item["name"])
                models_layout.addWidget(cb)
                # store per-model enabled flags
                self.models_enabled[item["name"]] = True
                cb.toggled.connect(
                    lambda checked, it=item: self.controlnet_model_toggled(
                        it, checked
                    )
                )

            # Wire the controlnet checkbox to enable/disable the models container and update flags
            def _on_controlnet_toggled(
                val,
                container=models_container,
                flag=controlnet_flag,
                models=models,
            ):
                # enable/disable the models container
                container.setEnabled(bool(val))
                self.models_enabled[flag] = bool(val)
                # When disabling, also mark all children models as False (so downloads skip them)
                if not val:
                    for m in models:
                        self.models_enabled[m["name"]] = False
                    for cb_child in container.findChildren(QCheckBox):
                        cb_child.setChecked(False)
                        cb_child.setEnabled(False)
                else:
                    for m in models:
                        # leave individual model flags as-is or default to True
                        self.models_enabled.setdefault(m["name"], True)
                    for cb_child in container.findChildren(QCheckBox):
                        cb_child.setEnabled(True)
                self.update_total_size_label()

            # connect our toggle handler to the controlnet group's toggled signal
            controlnet_group.toggled.connect(_on_controlnet_toggled)

            # Wire the master checkbox to enable/disable the entire version block
            def _on_master_toggled(
                val,
                core_w=core_chk,
                control_group=controlnet_group,
                container=models_container,
                flag=master_flag,
                models=models,
                version=version,
            ):
                core_w.setEnabled(bool(val))
                control_group.setEnabled(bool(val))
                container.setEnabled(bool(val) and control_group.isChecked())
                self.models_enabled[flag] = bool(val)
                core_flag_key = f"core_{version}"
                controlnet_flag_key = f"controlnet_{version}"
                if not val:
                    # disable internal flags and checkboxes
                    self.models_enabled[core_flag_key] = False
                    self.models_enabled[controlnet_flag_key] = False
                    for m in models:
                        self.models_enabled[m["name"]] = False
                    for cb_child in container.findChildren(QCheckBox):
                        cb_child.setChecked(False)
                        cb_child.setEnabled(False)
                    core_w.setChecked(False)
                    control_group.setChecked(False)
                else:
                    # restore defaults
                    self.models_enabled.setdefault(core_flag_key, True)
                    self.models_enabled.setdefault(controlnet_flag_key, True)
                    for m in models:
                        self.models_enabled.setdefault(m["name"], True)
                    for cb_child in container.findChildren(QCheckBox):
                        cb_child.setEnabled(True)
                self.update_total_size_label()

            # connect the version group's toggled signal
            version_group.toggled.connect(_on_master_toggled)

            # Add the version group to the top-level inner scroll area's layout
            try:
                top_inner_layout.addWidget(version_group)
            except Exception:
                # fallback: add directly if top scroll area wasn't created
                self.ui.stable_diffusion_layout.layout().addWidget(
                    version_group
                )

        # final spacer inside the stable diffusion group
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.ui.stable_diffusion_layout.layout().addItem(spacer)

        # Add Upscaler (x4) option (but place it outside the scroll area below the version groups)
        try:
            from airunner.components.art.data.bootstrap.sd_file_bootstrap_data import (
                SD_FILE_BOOTSTRAP_DATA,
            )

            upscaler_size = 0
            if SD_FILE_BOOTSTRAP_DATA.get(
                "Upscaler"
            ) and SD_FILE_BOOTSTRAP_DATA["Upscaler"].get("x4"):
                # Very rough size estimate per file (~5-10 MB each) unless more accurate sizes are known
                upscaler_size = len(
                    SD_FILE_BOOTSTRAP_DATA["Upscaler"]["x4"]
                ) * (6 * 1024 * 1024)
        except Exception:
            upscaler_size = 6 * 1024 * 1024

        self.models_enabled["upscaler_x4"] = True

        upscaler_checkbox = QCheckBox(self)
        upscaler_checkbox.setText("SD x4 Upscaler")
        upscaler_checkbox.setChecked(True)
        upscaler_checkbox.setObjectName("upscaler_x4")
        upscaler_checkbox.toggled.connect(self.upscaler_toggled)
        self._upscaler_size_estimate = upscaler_size

        # Place core widgets and the upscaler inside the Stable Diffusion top-level scroll area
        try:
            target_layout = top_inner_layout
        except Exception:
            target_layout = None

        if target_layout is None:
            # Fallback to placing them in the stable_diffusion_layout if the top scroll area isn't available
            target_layout = self.ui.stable_diffusion_layout.layout()

        for name, widget in self._core_widgets:
            try:
                target_layout.addWidget(widget)
            except Exception:
                pass

        try:
            target_layout.addWidget(upscaler_checkbox)
            # Add a horizontal separator after the upscaler, but place it in the main grid
            from PySide6.QtWidgets import QFrame

            hr = QFrame(self)
            hr.setFrameShape(QFrame.HLine)
            hr.setFrameShadow(QFrame.Sunken)
            try:
                # place the horizontal line in the main grid below the other top-level checkboxes
                self.ui.gridLayout.addWidget(hr, 8, 0, 1, 1)
            except Exception:
                # fallback: add to the target layout if grid layout isn't available
                target_layout.addWidget(hr)
        except Exception:
            pass

        # Do not reparent the top-level generated checkboxes; leave them in the main grid layout.
        # The UI template places ministral, e5 (embedding), speecht5, openvoice, and whisper at top-level
        # and they should remain there so their grid positions are preserved.

        self.update_total_size_label()

    def update_total_size_label(self):
        # Sizes are tracked in bytes
        mistral_size = 5.8 * 1024 * 1024
        whisper_size = 144.5 * 1024
        speecht5_size = 654.4 * 1024
        embedding_model_size = 1.3 * 1024 * 1024

        total_bytes = 0

        if self.models_enabled.get("stable_diffusion", False):
            # core items
            if self.models_enabled.get("safety_checker", False):
                total_bytes += 1.2 * 1024 * 1024
            if self.models_enabled.get("feature_extractor", False):
                total_bytes += 1.7 * 1024 * 1024

            # controlnet models grouped by version
            from collections import defaultdict

            version_group = defaultdict(list)
            for item in controlnet_bootstrap_data:
                version_group[item["version"]].append(item)

            for version, models in version_group.items():
                controlnet_flag = f"controlnet_{version}"
                if not self.models_enabled.get(controlnet_flag, False):
                    continue
                for model in models:
                    if not self.models_enabled.get(model["name"], False):
                        continue
                    # model['size'] may be a string; default to 700k if absent
                    try:
                        total_bytes += int(model.get("size", 722600))
                    except Exception:
                        total_bytes += 722600

        # Add other model categories
        if self.models_enabled.get("mistral", False):
            total_bytes += mistral_size
        if self.models_enabled.get("whisper", False):
            total_bytes += whisper_size
        if self.models_enabled.get("speecht5", False):
            total_bytes += speecht5_size
        if self.models_enabled.get("embedding_model", False):
            total_bytes += embedding_model_size
        if self.models_enabled.get("openvoice_model", False):
            total_bytes += 4.5 * 1024 * 1024

        # Add upscaler estimate if enabled
        if self.models_enabled.get("upscaler_x4", False):
            total_bytes += getattr(
                self, "_upscaler_size_estimate", 6 * 1024 * 1024
            )

        # Format human readable
        if total_bytes >= 1024 * 1024:
            size_str = f"{total_bytes / (1024 * 1024):.2f} GB"
        elif total_bytes >= 1024:
            size_str = f"{total_bytes / 1024:.2f} MB"
        else:
            size_str = f"{total_bytes:.2f} KB"
        self.ui.total_size_label.setText(size_str)

    @Slot(bool)
    def stable_diffusion_toggled(self, val: bool):
        self.models_enabled["stable_diffusion"] = val
        self.update_total_size_label()

    @Slot(bool)
    def whisper_toggled(self, val: bool):
        self.models_enabled["whisper"] = val
        self.update_total_size_label()

    @Slot(bool)
    def ministral_toggled(self, val: bool):
        self.models_enabled["mistral"] = val
        self.update_total_size_label()

    @Slot(bool)
    def embedding_model_toggled(self, val: bool):
        self.models_enabled["embedding_model"] = val
        self.update_total_size_label()

    @Slot(bool)
    def speecht5_toggled(self, val: bool):
        self.models_enabled["speecht5"] = val
        self.update_total_size_label()

    @Slot(bool)
    def openvoice_toggled(self, val: bool):
        self.models_enabled["openvoice_model"] = val
        self.update_total_size_label()

    @Slot(bool)
    def controlnet_model_toggled(self, item, val: bool):
        # update per-model flag
        self.models_enabled[item["name"]] = val

        # Determine if any stable-diffusion related option remains enabled
        any_enabled = False
        # core items
        if self.models_enabled.get(
            "safety_checker", False
        ) or self.models_enabled.get("feature_extractor", False):
            any_enabled = True
        # upscaler
        if self.models_enabled.get("upscaler_x4", False):
            any_enabled = True
        # per-version controlnet
        for k, v in list(self.models_enabled.items()):
            if k.startswith("controlnet_") and v:
                any_enabled = True
                break

        self.models_enabled["stable_diffusion"] = any_enabled

        self.update_total_size_label()

    def _core_version_toggled(self, flag: str, val: bool):
        """Handler for per-version core files checkbox (e.g. core_1.5)."""
        self.models_enabled[flag] = bool(val)
        # Recalculate whether any stable-diffusion related option remains enabled
        self._recalc_stable_diffusion_enabled()
        self.update_total_size_label()

    def _core_toggled(self, name: str, val: bool):
        """Handler for top-level core items like safety_checker and feature_extractor."""
        self.models_enabled[name] = bool(val)
        self._recalc_stable_diffusion_enabled()
        self.update_total_size_label()

    def _recalc_stable_diffusion_enabled(self):
        """Update the global stable_diffusion enabled flag based on current selections."""
        any_enabled = False
        if self.models_enabled.get(
            "safety_checker", False
        ) or self.models_enabled.get("feature_extractor", False):
            any_enabled = True
        if self.models_enabled.get("upscaler_x4", False):
            any_enabled = True
        for k, v in list(self.models_enabled.items()):
            if k.startswith("controlnet_") and v:
                any_enabled = True
                break
        self.models_enabled["stable_diffusion"] = any_enabled

    @Slot(bool)
    def upscaler_toggled(self, val: bool):
        """Toggle handler for the SD x4 Upscaler checkbox."""
        self.models_enabled["upscaler_x4"] = val
        self.update_total_size_label()
