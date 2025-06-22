# Stable Diffusion Settings Widget

This widget allows users to configure Stable Diffusion model settings, including selecting and importing custom model files.

## Model Import Workflow
- When browsing for a model file, the user is prompted to import the model into the AI Runner folder.
- The dialog includes a "Do not ask again" checkbox, which is persisted in QSettings.
- If the user chooses to import, the file is copied to the correct model storage path (see `airunner/utils/model_utils/model_utils.py`), with a progress dialog shown during the copy.

## Key Utilities
- `get_stable_diffusion_model_storage_path`: Determines the correct storage path for model files.
- QSettings (via `get_qsettings`): Used to persist the "Do not ask again" preference.

## UI/UX
- Uses PySide6's `QProgressDialog` for file copy progress.
- All file operations are performed in a background thread to keep the UI responsive.

## Extending
- To change the model storage location, update the logic in `get_stable_diffusion_model_storage_path`.
- To reset the "Do not ask again" prompt, clear the `import_model_dont_ask_again` key in QSettings.
