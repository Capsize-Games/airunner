from PySide6.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
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
from airunner.components.data.bootstrap_service import (
    get_model_bootstrap_data,
)


class ChooseModelsPage(BaseWizard):
    class_name_ = Ui_install_success_page

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models_enabled = {
            "stable_diffusion": True,
            "whisper": True,
            "llm": True,
            "embedding_model": True,
            "openvoice_model": True,
        }

        # Prepare core items (safety checker, feature extractor)
        core_items = [
        ]

        # Prepare core items (these will be placed outside the scroll area in the main grid)
        self._core_widgets = []
        for item in core_items:
            chk = QCheckBox(self)
            chk.setText(item["display_name"])
            chk.setChecked(True)
            chk.setObjectName(item["name"])
            self.models_enabled[item["name"]] = True
            self._core_widgets.append((item["name"], chk))

        # Expose the stable-diffusion model bootstrap list for the installer
        self.models = get_model_bootstrap_data()

        # Make the groupBox act as a checkable 'Stable Diffusion' group
        try:
            self.ui.groupBox.setTitle("Art Models")
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

        # Add Z-Image version groups (core files only).
        from PySide6.QtWidgets import QGroupBox

        zimage_versions = [
            model["version"]
            for model in self.models
            if model.get("category") == "zimage"
        ]
        for version in sorted(set(zimage_versions)):
            zimage_group = QGroupBox(self)
            zimage_layout = QVBoxLayout(zimage_group)

            master_flag = f"sd_{version}"
            self.models_enabled[master_flag] = True
            zimage_group.setTitle(version)
            zimage_group.setCheckable(True)
            zimage_group.setChecked(True)

            core_chk = QCheckBox("Core files", self)
            core_flag = f"core_{version}"
            self.models_enabled[core_flag] = True
            core_chk.setChecked(True)
            core_chk.toggled.connect(
                lambda val, flag=core_flag: self._core_version_toggled(
                    flag, val
                )
            )
            zimage_layout.addWidget(core_chk)

            def _on_art_master_toggled(
                val,
                core_w=core_chk,
                flag=master_flag,
                core_flag_key=core_flag,
            ):
                core_w.setEnabled(bool(val))
                self.models_enabled[flag] = bool(val)
                if not val:
                    self.models_enabled[core_flag_key] = False
                    core_w.setChecked(False)
                else:
                    self.models_enabled.setdefault(core_flag_key, True)
                self.update_total_size_label()

            zimage_group.toggled.connect(_on_art_master_toggled)

            try:
                top_inner_layout.addWidget(zimage_group)
            except Exception:
                self.ui.stable_diffusion_layout.layout().addWidget(
                    zimage_group
                )

        # final spacer inside the stable diffusion group
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.ui.stable_diffusion_layout.layout().addItem(spacer)

        # Add Upscaler (x4) option (but place it outside the scroll area below the version groups)
        try:
            from airunner.components.data.bootstrap_service import (
                get_sd_file_bootstrap_data,
            )

            upscaler_size = 0
            if get_sd_file_bootstrap_data().get(
                "Upscaler"
            ) and get_sd_file_bootstrap_data()["Upscaler"].get("x4"):
                # Very rough size estimate per file (~5-10 MB each) unless more accurate sizes are known
                upscaler_size = len(
                    get_sd_file_bootstrap_data()["Upscaler"]["x4"]
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

                # Do not reparent the top-level generated checkboxes; leave them in the main grid layout.\n        # The UI template places the local-LLM, e5, openvoice, and whisper\n        # checkboxes at top-level and they should remain there so their grid\n        # positions are preserved.

        self.update_total_size_label()

    def _llm_size_estimate(self) -> int:
        """Return the total size for enabled local LLM bootstrap files."""
        if not self.models_enabled.get("llm", False):
            return 0

        from airunner_services.llm.provider_config import (
            LLMProviderConfig,
        )
        from airunner.components.data.bootstrap_service import (
            get_llm_file_bootstrap_data,
        )

        total = 0
        for model in get_model_bootstrap_data():
            if model.get("category") != "llm":
                continue
            if model.get("pipeline_action") == "embedding":
                continue
            download_info = LLMProviderConfig.resolve_download_target(
                "local",
                repo_id=model["path"],
                prefer_pre_quantized=True,
            )
            repo_id = download_info["repo_id"] if download_info else model["path"]
            total += sum(get_llm_file_bootstrap_data()[repo_id]["files"].values())
        return total

    def update_total_size_label(self):
        # Sizes are tracked in bytes
        llm_size = self._llm_size_estimate()
        whisper_size = 144.5 * 1024
        embedding_model_size = 1.3 * 1024 * 1024
        zimage_core_sizes = {}
        try:
            from airunner.components.data.bootstrap_service import (
                get_sd_file_bootstrap_data,
            )

            for model in self.models:
                if model.get("category") != "zimage":
                    continue
                version = model.get("version")
                files = get_sd_file_bootstrap_data().get(version, {}).get(
                    "txt2img",
                    {},
                )
                zimage_core_sizes[version] = sum(
                    size
                    for size in files.values()
                    if isinstance(size, int)
                )
        except Exception:
            zimage_core_sizes = {}

        total_bytes = 0

        if self.models_enabled.get("stable_diffusion", False):
            for version, size in zimage_core_sizes.items():
                if self.models_enabled.get(f"core_{version}", False):
                    total_bytes += size

        # Add other model categories
        if self.models_enabled.get("llm", False):
            total_bytes += llm_size
        if self.models_enabled.get("whisper", False):
            total_bytes += whisper_size
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
    def llm_toggled(self, val: bool):
        self.models_enabled["llm"] = val
        self.update_total_size_label()

    @Slot(bool)
    def embedding_model_toggled(self, val: bool):
        self.models_enabled["embedding_model"] = val
        self.update_total_size_label()

    @Slot(bool)
    def openvoice_toggled(self, val: bool):
        self.models_enabled["openvoice_model"] = val
        self.update_total_size_label()

    def _core_version_toggled(self, flag: str, val: bool):
        """Handler for per-version core files checkbox (e.g. core_1.5)."""
        self.models_enabled[flag] = bool(val)
        # Recalculate whether any stable-diffusion related option remains enabled
        self._recalc_stable_diffusion_enabled()
        self.update_total_size_label()

    def _core_toggled(self, name: str, val: bool):
        """Handler for top-level core items """
        self.models_enabled[name] = bool(val)
        self._recalc_stable_diffusion_enabled()
        self.update_total_size_label()

    def _recalc_stable_diffusion_enabled(self):
        """Update the global stable_diffusion enabled flag based on current selections."""
        any_enabled = False
        if self.models_enabled.get("upscaler_x4", False):
            any_enabled = True
        for k, v in list(self.models_enabled.items()):
            if k.startswith("core_") and v:
                any_enabled = True
                break
        self.models_enabled["stable_diffusion"] = any_enabled

    @Slot(bool)
    def upscaler_toggled(self, val: bool):
        """Toggle handler for the SD x4 Upscaler checkbox."""
        self.models_enabled["upscaler_x4"] = val
        self.update_total_size_label()
