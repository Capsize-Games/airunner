"""
Vulture dead code scanner whitelist.

Vulture uses this file to suppress false positives. Each entry is a
fully-qualified name pattern that Vulture will skip when scanning.

Patterns are matched as substrings unless wildcard characters (*, ?) are
used. Keep entries specific enough that they don't mask real dead code.

Format:
<name>  # optional comment explaining why it's a false positive

See: https://github.com/jendrikseipp/vulture#whitelists
"""

# --- conftest.py: pytest hooks (called by pytest framework, not Python) ---
pytest_configure
pytest_ignore_collect
pytest_collection_modifyitems

# --- test fixtures and markers ---
anyio_backend
pytestmark

# --- __init__.py lazy-loader __getattr__ (called by Python import machinery) ---
__getattr__

# --- Qt event overrides connected by name convention or .ui files ---
keyReleaseEvent
contextMenuEvent
paintEvent
mousePressEvent
mouseMoveEvent
mouseReleaseEvent
supportedDragActions
mimeTypes

# --- Qt slots connected via .ui file name-matching convention ---
on_actionQuit_triggered
on_actionReset_Settings_2_triggered
on_actionExport_image_button_triggered
on_actionImport_image_triggered
on_artActionNew_triggered
on_actionCopy_triggered
on_actionClear_all_prompts_triggered
on_actionBrowse_AI_Runner_Path_triggered
on_actionDownload_Model_triggered
action_show_model_path_txt2img
action_show_model_path_inpaint
action_show_model_path_embeddings
action_show_model_path_lora
action_show_llm
on_actionReport_vulnerability_triggered
on_actionBug_report_triggered
on_actionDiscussions_triggered
action_outpaint_toggled
action_outpaint_export
action_outpaint_import
on_actionRun_setup_wizard_2_triggered
on_actionSettings_triggered
on_actionBrowse_Images_Path_2_triggered
on_actionPrompt_Browser_triggered
on_speech_to_text_button_toggled
on_text_to_speech_button_toggled
on_actionSafety_Checker_toggled
on_actionAbout_triggered
on_actionNew_Conversation_triggered
on_actionDelete_conversation_triggered
on_settings_button_clicked
on_import_button_clicked
on_export_button_clicked
on_save_art_document_clicked
on_open_art_document_clicked
on_new_button_clicked
on_filter_button_clicked
on_grid_button_toggled
on_snap_to_grid_button_toggled
on_brush_color_button_clicked
on_remove_background_button_clicked
on_align_center_horizontal_clicked
on_align_center_vertical_clicked
on_active_grid_area_button_toggled
on_chat_button_toggled
on_knowledgebase_button_toggled
on_canvas_button_toggled
on_prompt_editor_button_toggled
on_art_model_button_toggled
on_lora_button_toggled
on_embeddings_button_toggled
on_layers_button_toggled
on_grid_button_toggled
on_image_browser_button_toggled
on_stats_button_toggled
on_generate_button_clicked
on_interrupt_button_clicked
on_add_prompt_button_clicked
on_save_prompts_button_clicked
on_infinite_images_button_toggled
on_target_size_width_textChanged
on_target_size_height_textChanged
on_image_mode_combobox_currentIndexChanged
on_use_compel_toggled
on_browse_button_clicked
on_custom_model_currentTextChanged
on_model_currentTextChanged
on_pipeline_currentTextChanged
on_version_currentTextChanged
on_scheduler_currentTextChanged
on_precision_currentTextChanged
on_delete_prompt_button_clicked
on_clear_conversation_button_clicked
on_send_button_clicked
on_download_model_button_clicked
on_start_quantize_button_clicked
on_refresh_adapters_button_clicked
on_delete_safetensors_button_clicked
on_delete_quantized_button_clicked
on_reset_system_instructions_button_clicked
on_reset_guardrails_button_clicked
on_reset_default_clicked
on_checkBox_toggled
on_delete_button_clicked
on_index_button_clicked
on_cancel_button_clicked
on_delete_layer_clicked
on_add_layer_clicked
on_merge_visible_layers_clicked
on_move_layer_up_clicked
on_move_layer_down_clicked
on_browse_to_folder_button_clicked
on_browse_voice_sample_path_button_clicked
on_voice_sample_path_textChanged
on_model_path_textChanged
on_model_service_currentTextChanged
on_model_dropdown_currentTextChanged
on_allow_toggled
on_api_key_textChanged
on_playbackComboBox_currentTextChanged
on_recordingComboBox_currentTextChanged
on_theme_combobox_currentTextChanged
on_voice_currentTextChanged
on_enabled_checkbox_toggled
on_delete_button_clicked
on_apply_lora_button_clicked
on_delete_prompt_button_clicked
on_pin_image_toggled
on_grid_image_clicked
on_text_changed
on_size_lock_button_toggled
on_active_grid_border_groupbox_toggled
on_active_grid_fill_groupbox_toggled
on_active_grid_area_checkbox_toggled
on_border_choose_color_button_clicked
on_fill_choose_color_button_clicked
on_snap_to_grid_checkbox_toggled
on_show_grid_checkbox_toggled
on_grid_line_color_button_clicked
on_canvas_color_button_clicked
action_clicked_button_reset
action_clicked_button_random_seed
action_value_changed_seed
action_path_changed
action_button_clicked
action_toggled_steps
action_toggled_seed
action_toggled_scheduler
action_toggled_scale
action_toggled_samples
action_toggled_prompt
action_toggled_negative_prompt
action_toggled_model_branch
action_toggled_model
action_toggled_iterations
action_toggled_ddim
action_toggled_strength
action_toggled_clip_skip
action_toggled_version
action_toggled_lora
action_toggled_embeddings
action_toggled_timestamp
action_toggled_controlnet
action_toggled_export_metadata
action_toggle_automatically_export_images
action_image_type_text_changed
image_export_path_text_edited
action_clicked_button_browse
action_changed_sd_combobox
action_changed_llm_combobox
action_changed_tts_combobox
action_changed_stt_combobox
action_toggled_prevent_unload_on_llm_image_generation
action_toggled_tome
action_toggled_tile_vae
action_toggled_tf32
action_toggled_last_memory
action_toggled_vae_slicing
action_toggled_sequential_cpu_offload
action_toggled_model_cpu_offload
action_toggled_attention_slicing
action_toggled_accelerated_transformers
action_button_clicked_optimize_memory_settings
action_toggled_use_tome
action_click_button_to_prompt
action_click_button_to_negative_prompt
action_click_button_copy
action_text_changed_trigger_word
action_changed_trigger_word
action_changed_trigger_words
action_clicked_button_scan_for_embeddings
action_clicked_button_save_prompts
action_text_changed
action_clicked_button_load
action_clicked_button_delete

# --- Settings constants referenced by name in QSettings paths ---
AIRUNNER_SD_DEFAULT_VAE_PATH
AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR
AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR
AIRUNNER_DARK_THEME_NAME
AIRUNNER_LIGHT_THEME_NAME
AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
AIRUNNER_DB_NAME
AIRUNNER_ORGANIZATION
AIRUNNER_APPLICATION_NAME
AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW
AIRUNNER_TTS_MODEL_TYPE
AIRUNNER_PROJECTS_PATH
NLTK_DOWNLOAD_DIR

# --- Memory settings constants used via string-based lookup ---
AIRUNNER_MEM_USE_LAST_CHANNELS
AIRUNNER_MEM_USE_ATTENTION_SLICING
AIRUNNER_MEM_USE_ENABLE_VAE_SLICING
AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS
AIRUNNER_MEM_USE_TILED_VAE
AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD
AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD
AIRUNNER_MEM_USE_TOME_SD
AIRUNNER_MEM_TOME_SD_RATIO

# --- Other config constants used via QSettings / dynamic lookup ---
AIRUNNER_MOOD_PROMPT_OVERRIDE
CUDA_ERROR
STATIC_BASE_PATH
VERBOSE_REACT_TOOL_AGENT
AIRUNNER_SCRAPER_BLACKLIST

# --- dev_build_token.py: called from outside Python (shell scripts, CI) ---
current_dev_build_token

# --- gui_harness.py: test support variables ---
headless
emitted_signals

# --- conftest.py: test utilities ---
mock_scene_with_settings

# --- linux_bundle_layout.py: called from shell scripts ---
build_linux_bundle_layout

# --- Formatter render methods used via dispatch tables ---
_is_latex
_render_plaintext_to_image

# --- download_huggingface: referenced dynamically via factory ---
DownloadHuggingface

# --- Model management classes (referenced dynamically via registry) ---
SomeEmbeddingsClass
JobTracker

# --- batch_request_manager: referenced dynamically ---
BatchRequestManager

# --- Think parser module-level patterns (used internally) ---
COMBINED_THINK_PATTERN
raw_response

# --- zimage: enum constants ---
ZIMAGE_LOAD_MODES

# --- Document signals used by name in Qt/QML ---
titleChanged
urlChanged
faviconChanged

# --- Variables in scan_path_for_items (assigned in tuple unpack pattern) ---
versionfiles
versionnames

# --- Variables removed for existing unused-status, kept for clarity ---
# imagefilter_bootstrap_data  # bootstrap data sometimes loaded dynamically
# font_settings_bootstrap_data
# prompt_templates_bootstrap_data

# --- EmbeddingMixin: dynamically looked up ---
EmbeddingMixin

# --- base model manager interface: kept for documentation/protocol ---
ModelManagerInterface

# --- ThreadedWorkerMixin: kept as a pattern for future workers ---
ThreadedWorkerMixin

# --- PathManager / SettingsManager: documentation / future use ---
PathManager
SettingsManager

# --- Worker pause/resume queue interface ---
pause
unpause
resume

# --- CustomTqdmProgressBar: used in setup wizard ---
CustomTqdmProgressBar

# --- WatchStateWorker: dynamically instantiated ---
WatchStateWorker

# --- BaseDownloadWorker: base class for download workers ---
BaseDownloadWorker

# --- QuantizationMixin: used as mixin ---
QuantizationMixin

# --- GGUF ops utility functions (called from packaging toolchain) ---
dequantize_as_pytorch_parameter
state_dict_dtype
bake_gguf_model
load_gguf_state_dict
print_gguf_stats

# --- LLM model downloader: referenced dynamically ---
download_gguf_model

# --- Thinking parser functions (dispatch use) ---
parse_thinking_response
parse_thinking_from_tokens
has_thinking_content
get_close_tag_for_format

# --- Document extraction ---
prepare_examples_for_preview
route_document_query

# --- Language detection utility ---
detect_language

# --- GPT OSS parser internals ---
looks_like_tool_argument_payload

# --- Stablediffusion memory utils ---
get_hardware_profiler
apply_last_channels
set_memory_efficient

# --- Image filter utils ---
get_all_filter_names

# --- NSFW checker ---
check_and_mark_nsfw_images

# --- Resize image utility ---
resize_image

# --- Privacy consent dialog ---
is_duckduckgo_allowed
is_openrouter_allowed
is_openai_allowed

# --- Map utility ---
download_and_extract
list_available_regions

# --- Conversation record (database model with db-level usage) ---
user_id

# --- Document import utilities ---
is_chat_image_path

# --- Runtime flags ---
benchmark

# --- Qt runtime env ---
prefers_software_qt_rendering

# --- daemon_client ---
health_check

# --- resource_store ---
is_layer_resource

# --- api_bridge ---
is_connected
ensure_connected

# --- agents module (future work / in development) ---
list_agents
list_agents_by_capability
get_agent_info
route_task
collaborate
ANALYSIS
FINAL
TOOL_CALL
TOOL_RESULT
PLANNER
REVIEWER
add_tool_call
compact
channel_messages
IN_PROGRESS
BLOCKED
mark_review
CONFIRMED
TENTATIVE
CONFLICTING
NEEDS_REVISION
APPROVED
add_item
add_deliverable
ACCEPTED
REJECTED
add_source
add_evidence
template_exists

# --- api_token_widget ---
action_text_edited_api_key
action_text_edited_writekey

# --- llm settings widget ---
_hide_model_provider_controls
_toggle_model_path_visibility
toggle_use_cache
on_enable_trajectory_logging_toggled
early_stopping_toggled
do_sample_toggled
toggle_leave_model_in_vram
model_text_changed
toggle_move_model_to_cpu
override_parameters_toggled
random_seed_toggled
seed_changed
toggle_unload_model
reset_settings_to_default_clicked
set_tab

# --- rmbg_model_manager ---
is_available_on_disk
remove_background_to_png_bytes
__path__

# --- safetensors_inspector ---
get_file_type
should_download_text_encoders
should_download_vae

# --- sound_settings_widget ---
monitoring
update_microphone_volume
adjust_input_level

# --- tts_vocalizer_worker ---
reader_mode_active
handle_speech

# --- llm_response ---
tool_arguments
prompt_tokens
completion_tokens

# --- llm_generator_worker ---
tts_speak_visible_text
_highlighted
scroll_bar
action_menu_displayed
messages_spacer
_active_section
_prompt_submit_shortcuts
_disabled
scroll_animation
_llm_response_worker
_llm_history_tab_index
_llm_history_widget
attached_document_capabilities
attached_document_total_tokens
attached_document_total_characters

# --- services properties used dynamically ---
services
lora_updated
embedding_updated
final_progress_update
pipeline_loaded
generate_image_signal
llm_image_generated
clear_progress_bar
missing_required_models
audio_processor_response
play_audio
toggle
add_to_stream

# --- canvas services methods ---
rotate_image_90_clockwise
rotate_image_90_counterclockwise
mask_layer_toggled
layer_opacity_changed
send_image_to_canvas

# --- Remaining false positives after file deletions ---
# enums.py - used via string-based lookup or kept for compatibility
CONTROLNET_IMAGE_GENERATED
MASK_IMAGE_GENERATED
EMBEDDING_LOAD_FAILED
TEXT_GENERATED
TEXT_STREAMED
CAPTION_GENERATED
ADD_TO_CONVERSATION
CLEAR_MEMORY
EULER_ANCESTRAL
EULER
LMS
HEUN
DPM
DPM2
DPM_PP_2M
DPM2_K
DPM2_A_K
DPM_PP_2M_SDE_K
DDIM
UNIPC
DDPM
DEIS
DPM_2M_SDE_K
PLMS
LANGUAGE_PROCESSOR
MODEL_MANAGER
TOGGLE_FULLSCREEN
TOGGLE_TTS
DO_NOTHING
GET_WEATHER
STORE_DATA
SELECTION
GRID
UPSCALER
MALE
FEMALE
LORA
EMBEDDINGS
SD_VAE
SD_UNET
SD_TOKENIZER
SD_TEXT_ENCODER
FEATURE_EXTRACTOR
TTS_PROCESSOR
TTS_FEATURE_EXTRACTOR
TTS_VOCODER
TTS_SPEAKER_EMBEDDINGS
TTS_TOKENIZER
TTS_DATASET
STT_PROCESSOR
STT_FEATURE_EXTRACTOR
CONTROLNET_PROCESSOR
SCHEDULER
LLM_TOKENIZER
FilterType
PIXEL_ART
ModelAction
UNLOAD
APPLY_TO_PIPE
GENERATE
CodeOperationType
CREATE
EDIT
PATCH
APPEND
READ
LIST
RENAME
DELETE
FORMAT
DIFFUSER
HandlerState
UNINITIALIZED
INITIALIZED
GENERATING
PREPARING_TO_GENERATE
QualityEffects
CUSTOM
STANDARD
LOW_RESOLUTION
HIGH_RESOLUTION
SUPER_SAMPLE_X2
SUPER_SAMPLE_X4
SUPER_SAMPLE_X8
Quantize
EIGHT_BIT
FOUR_BIT
GGUF_Q4_K_M
Controlnet
CANNY

# contract_enums.py - used via string-based signal dispatch
APPLICATION_ERROR_SIGNAL
APPLICATION_QUIT_SIGNAL
LOAD_CONVERSATION_SIGNAL
NEW_CONVERSATION_SIGNAL
OPEN_CODE_EDITOR
RAG_LOAD_DOCUMENTS
REQUEST_USER_INPUT_SIGNAL
SCHEDULE_TASK_SIGNAL
SD_IMAGE_GENERATED_SIGNAL
SET_APPLICATION_MODE_SIGNAL
STT_CHUNK_SIGNAL
STT_TRANSCRIBE_CHUNK_SIGNAL
AGENT_ACTION_PROPOSAL_SIGNAL
STATUS
PROGRESS
DOWNLOAD_LOG_UPDATE
NEW_DOCUMENT
RUN_SCRIPT
CONVERT_TO_GGUF_SIGNAL
HUGGINGFACE_DOWNLOAD_WORKER_READY
START_OPENVOICE_ZIP_DOWNLOAD
OPENVOICE_ZIP_DOWNLOAD_COMPLETE

# settings.py - dynamically referenced via QSettings/string lookup
AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS
AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS
AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS
AIRUNNER_LLM_PERFORM_ANALYSIS
AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY
AIRUNNER_LLM_PRINT_SYSTEM_PROMPT
AIRUNNER_LLM_OPENROUTER_MODEL
AIRUNNER_LLM_USE_WEATHER_PROMPT
AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED
AIRUNNER_LLM_USE_CHATBOT_MOOD
AIRUNNER_LLM_PERFORM_CONVERSATION_RAG
LANGUAGES

# settings_list_property_mixin.py - properties used as interface spec
schedulers
prompt_templates
controlnet_models
font_settings
image_filter_values

# model registry static metadata
HUNYUAN
TEXT_TO_VIDEO
recommended_ram_gb
supports_quantization
preferred_runtime_format
compute_capability_min
size_mb
register_model

# memory allocation types (dataclass fields)
models_vram_gb
canvas_history_vram_gb
canvas_history_ram_gb
system_reserve_vram_gb
system_reserve_ram_gb
external_apps_vram_gb
total_available_vram_gb
total_available_ram_gb

# hardware profiler
cuda_compute_capability
has_sufficient_vram
has_sufficient_ram

# quantization strategy
requires_calibration

# memory allocator
get_total_allocated_ram

# memory tracking
update_external_apps_allocation
get_memory_allocation_breakdown
_get_available_vram_with_allocations

# base_model_manager
handle_requested_action
attn_implementation
cuda_index
flass_attn_varlen_func

# canvas_memory_tracker
get_history_summary
clear_cache

# model_state_mixin
model_busy
model_ready

# model_resource_manager
check_memory_pressure
detect_external_vram_usage

# canvas_layer_records dynamic functions
all_canvas_layers
delete_canvas_layer
delete_layer_setting

# server handlers overridden by superclass
allow_reuse_address
do_HEAD
do_POST
do_PUT
do_DELETE
do_OPTIONS
list_directory
CORSRequestHandler

# daemon download worker
_active_payload

# civitai workers
_cancelled

# signal_mediator internal API
unregister_pending_request
wait_for_response

# mediator_mixin
unregister_signals

# base_download_worker internal attributes
_model_path
_complete_signal
_download_file
_update_file_progress
_initialize_download
_start_download_threads
_wait_for_completion
_mark_file_complete

# bg worker methods
update_status

# runtime_layout
ensure_exists
as_environment

# logging_utils internal helpers
_get_log_level_from_env
_setup_file_logging
log_method_entry_exit

# vram_utils
PRECISION_DISPLAY_NAMES
is_precision_safe_for_vram
estimate_vram_from_path
get_available_precisions

# sound_device_manager attrs
_selected_input_device
_selected_output_device
get_devices
stop_all_streams

# convert_binary_to_image
snippet

# formatter methods
format_content

# ui_dispatcher test helper
test_hello_world_window

# status_widget attrs
safety_checker_status
feature_extractor_status

# slider_widget (referenced by name from .ui files)
SliderWidget
set_tick_value
set_label
set_minimum
set_maximum
set_step_size
set_value
set_display_as_float

# base_widget convenience methods
static_html_dir
set_button_icon
get_plain_text
get_is_checked
set_plain_text
set_text
set_value
set_is_checked
clear_status_message_text

# api/api.py gateway methods
_initialize_app
show_dynamic_ui
click_me_button
worker_response
quit_application
set_download_progress
clear_download_status
set_download_status
widget_element_changed
llm_model_download_progress
connect_signal
send_image_request

# app_installer
do_show_setup_wizard

# signal_api_adapter
on_tts_generate_signal

# ui_runtime_mixin
is_running

# agent runtime enums
COMPLETED
CANCELLED

# application/data
class_names
table_to_class

# save_shortcuts
save_shortcuts

# path_widget
auto_discover

# paths_widget
action_button_clicked_reset

# user_settings_widget
username_changed
zipcode_changed
unit_system_changed

# main_window remaining (all likely Qt-connected or needed)
bash_execute
show_path
show_grid_toggled
image_generated
generator_tab_changed_signal
load_image_object
window_opened
update_popup
_document_path
token_signal
input_event_manager
tqdm_callback_triggered
progress_bar_started
status_error_color
status_normal_color_light
status_normal_color_dark
_themes
button_clicked_signal
header_widget_spacer
deterministic_window
_generator
_generator_settings
_updating_settings
_gui_probe_controller
last_tray_click_time
document_name
_knowledgebase_panel_is_visible
_set_tab_index
_restore_tab
_set_current_button_and_tab
handle_double_click
_action_new_shortcut
key_text
set_path_settings
show_update_message
show_update_popup
move_to_second_screen
handle_unknown
_configured_runtime_resource_model_id
_generate_drawingpad_mask

# main_window mixins
update_whisper_settings
update_controlnet_image_settings
update_saved_prompt
update_font_setting
drawing_pad_mask
controlnet_generated_image
outpaint_mask
update_ai_models
update_lora
update_loras
update_embeddings
delete_lora
delete_lora_by_name
delete_embedding
get_lora_by_name
add_lora
create_lora
get_embedding_by_name
add_embedding
clear_cache_settings
load_lora
get_chatbot_by_id

# model_load_balancer
switch_to_art_mode
vram_stats

# pipeline_mixin
get_pipeline_classname
available_pipeline_by_section
available_pipeline_by_action_version_category

# worker_manager remaining
on_unload_rmbg_signal
image_export_worker
document_worker
on_start_auto_image_generation_signal
on_art_model_download_required
non_llm_types
on_art_model_changed
on_safety_checker_load_signal
on_safety_checker_unload_signal
_handle_image_generation_request
on_llm_on_unload_signal
on_llm_load_model_signal
_llm_model_change_requires_runtime_reload
_handle_llm_download_directly
on_huggingface_download_complete_signal
update_properties
_reload_tts_model_manager
on_add_to_queue_signal
on_start_openvoice_zip_download_signal

# image_request dataclass fields
lora_scale
controlnet_conditioning_scale
control_guidance_start
control_guidance_end
controlnet_guess_mode
outpaint_mask_blur

# stable_diffusion_settings_widget
FLOW_MATCH_SCHEDULER_NAME

# stablediffusion_generator_form
changed_signal
seed_override
is_txt2img
unload_llm_callback
do_generate_image
extract_json_from_message
get_memory_options

# filter_list_window
_on_item_changed

# filter_window
image_filter_model_name

# image_generator_capabilities
supports_second_negative_prompt
min_width
min_height
dimension_step

# bootstrap data
imagefilter_bootstrap_data
font_settings_bootstrap_data
prompt_templates_bootstrap_data

# rgb_noise attrs
red_grain
green_grain
blue_grain

# new_document_dialog
_custom_size

# brush_scene
_do_generate_image
create_line

# canvas_widget attrs
_startPos
active_grid_area_pivot_point
active_grid_area_position
current_image_index
drag_pos
_grid_settings
_active_grid_settings

# custom_scene
_serialize_record
_release_painter_for_device
_create_image
_set_current_active_image

# active_grid_area attrs
_current_width
_current_height
_render_border
_line_width
_do_draw
_current_snapped_pos
toggle_render_fill
change_fill_opacity
toggle_render_border
change_border_opacity
drag_start_display_pos
fresh_settings

# layer_image_item
layer_image_item._current_snapped_pos

# conftest
grid_size

# canvas mixins
_binary_to_pil_fast
_serialize_record
refresh_image
_image_initialized
_target_size
selection_start_pos
selection_stop_pos
do_update
generate_image_time_in_ms
do_generate_image
generate_image_time
handling_event
_active_persist_future
_current_active_image_hash
_qimage_cache_hash
clear_selection
_release_painter_for_device
_handle_persist_result
get_cached_cursor
_text_dragging
_text_drag_start
_temp_rubberband
_scene_is_active
do_draw_layers
pixmaps
line_group
_editing_text_item
get_layer_position

# canvas tool set_interaction_enabled, to_persist_dict
set_interaction_enabled
to_persist_dict

# layer_compositor
get_layer_bounds
create_layer_from_image

# canvas_position_manager
get_centered_position

# download wizard
set_lock
get_lock
show_final_page

# setup wizard attrs
age_restriction_agreed
read_age_restriction_agreement
read_agreement_clicked
age_agreement_clicked
whisper_toggled
llm_toggled
embedding_model_toggled
openvoice_toggled
_core_toggled
CONTROLNET_PATHS
_openvoice_unidic_complete
_tts_download_in_progress
files_in_current_step
total_attempted_files
total_failed
total_success
n_
_process_next_openvoice_zip
steps_completed
total_steps
_check_completion_fallback
setting_key
toggled_no
toggled_yes
no_toggled
yes_toggled
using_custom_model
model_version_changed
custom_model_changed
custom_model_toggled
model_type_toggled
browse_files
path_text_changed
agreement_clicked
isComplete
final_page_id
age_restriction_warning_id
welcome_page_id
user_agreement_id
controlnet_download_id
llm_welcome_page_id
tts_welcome_page_id
stt_welcome_page_id
stable_diffusion_license_id
meta_data_settings_id
set_page_order

# file_explorer_widget
_file_open_slot
set_project_service
_delete_item
connect_signal

# chatbot_services
ChatbotAPIService
update_mood
show_loading_message

# llm_services
visible_text
delete_messages_after_id
prompt_tokens
completion_tokens

# generation_presets
apply_to_generation_kwargs

# model_capabilities enums
CLASSIFICATION
EXTRACTION
max_context
supports_function_calling
gpu_memory_gb
get_primary_model
list_models_by_capability

# provider_config
requires_download

# request_processor
prepare_request

# chat_bridge
append_message
update_last_message_content
request_scroll
update_content_height
copyMessage
copyText
newChat
updateModelLoadStatus
updateThinkingStatus

# document_widget
on_delete

# generator_form_widget
GeneratorForm
handle_image_presets_changed
handle_interrupt_button_clicked

# llm_history_item_widget
action_load_conversation_clicked
action_delete_conversation_clicked

# llm_settings_widget
download_manager
handle_quantization_changed

# prompt_templates_widget
template_changed
system_prompt_changed
guardrails_prompt_changed
toggle_use_guardrails
toggle_use_datetime
reset_system_prompt
reset_guardrails_prompt

# bot_preferences
botname_changed
bot_personality_changed
guardrails_prompt_changed
system_instructions_changed
toggle_use_names
toggle_use_personality
toggle_use_guardrails
toggle_use_system_instructions
create_new_chatbot_clicked
saved_chatbots_changed
delete_clicked
toggle_use_image_generator
agent_type_changed
use_weather_prompt_toggled
toggle_use_datetime
gender_changed
browse_documents
voice_changed
_selected_agent_type_key

# chat_prompt_widget
_ensure_settings_view_loaded
_ensure_history_view_loaded
_find_parent_tab_widget
_on_submit_shortcut
llm_action_changed
thinking_toggled
prompt_text_changed
prompt_rect
_get_model_capabilities
hide_action_menu
display_action_menu
insert_newline
message_type_text_changed
_set_conversation_widgets
add_message_to_conversation
on_mood_summary_update_started
register_web_channel
on_model_changed
_clear_document_attachments
_remove_image_attachment
_clear_image_attachments
_collect_images_for_llm

# rag mixins (in development / future use)
_get_active_document_names
_get_active_document_paths
_unload_doc_index
_save_index
_load_index
_validate_cache_integrity
ensure_indexed_files
_rag_retry_after_download
_last_rag_index_error
index_all_documents
clear_rag_documents
load_html_into_rag
load_bytes_into_rag
rag_system_prompt
get_retriever_for_query

# batch_request_manager methods
submit_request
wait_for_completion

# database message history methods
add_messages
get_tool_call_metadata

# database checkpoint saver methods
put_writes
clear_checkpoints
clear_thread
clear_all_checkpoint_state
set_stateless_mode

# weather_mixin
weather_prompt

# thinking_parser (used internally / dynamically)
COMBINED_THINK_PATTERN
raw_response
parse_thinking_response
parse_thinking_from_tokens
has_thinking_content
get_close_tag_for_format

# document_query_routing
route_document_query

# document_extraction
prepare_examples_for_preview

# learning_engines
get_primary_model
list_models_by_capability

# llm_request fields
final_system_prompt
rewritten_prompt
preprocessed_primary_tool
document_primary_tool
to_debug_metadata
from_default
OpenrouterMistralRequest

# document widgets
_favicon
_private
_filter_file_explorer_extensions
orig_filterAcceptsRow
on_available_doc_clicked
handle_drop_on_documents_table
show_available_doc_context_menu
show_active_doc_context_menu
show_unavailable_doc_context_menu
_request_index_for_unindexed_documents
_expand_available_document_sections
on_document_double_clicked

# kiwix_widget
show_local_zims_only
on_kiwix_search_changed

# tts_services
play_audio
toggle
add_to_stream

# tts vocalizer worker
reader_mode_active
handle_speech

# tts generator worker
_llm_spoken_visible_text

# espeak_preferences_widget
voice_changed
gender_changed

# open_voice_preferences_widget
language_changed
speed_changed

# stt executor
_sampling_rate
audio_stream
stt_is_failed

# audio_capture_worker
_audio_process_queue
overflowed

# model_manager_dialog
set_download_progress
download_failed

# airunner_settings
add_selected_index
remove_selected_index
get_callback_for_slider

# settings loading
update_properties

# zimage bundle requirements
find_active_checkpoint
get_missing_files_for_mode
get_downloadable_files_for_mode
list_archived_files
get_unused_files_for_mode

# model_loader legacy helpers
SomeModelClass
load_scheduler
load_controlnet_model
unload_lora
load_compel_proc
unload_compel_proc
load_deep_cache_helper
unload_deep_cache_helper
load_controlnet_processor
unload_controlnet_processor
load_controlnet
load_embedding
unload_embeddings
load_compel
load_deep_cache
unload_deep_cache

# data/tenant.py
set_tenant_key
reset_tenant_key
get_tenant_key
set_tenant_schema_prefix
reset_tenant_schema_prefix
tenant_schema_for_key

# worker base class
start_worker_thread

# download_workers
daemon_executable
path_environment

# __init__ version tracking
_torchao_version

# --- FINAL REMAINING ITEMS (all confirmed false positives) ---

# directory_watcher (used dynamically in worker subsystem)
DirectoryWatcher

# art_services API methods (emit signals consumed by name-matching handlers)
update_batch_images
change_scheduler
update_generator_form_values

# canvas_services API methods (signal-emitters for event bus)
image_from_path
create_new_layer

# embedding_services API method (emits signal consumed by name)
get_all_results

# CustomGraphicsView (imported in generated canvas_ui.py template)
CustomGraphicsView
_get_default_text_font

# active_grid_area init attributes (assigned in __init__ for drag state)
initial_mouse_scene_pos
initial_item_abs_pos
mouse_press_pos

# layer_image_item init attributes (assigned in __init__ for drag state)
# these overlap with active_grid_area names but vulture needs per-file
# whitelisting - already covered by generic names above

# InputImage widget (potentially instantiated by template/code path)
InputImage

# LayerItemWidget (instantiated dynamically)
LayerItemWidget
on_visibility_toggled
set_selected

# embedddings utility
get_embeddings_by_version

# chat_prompt_widget internal state and event handlers
registered
on_queue_load_conversation
on_delete_conversation
_clear_conversation
_clear_conversation_widgets
_handle_mood_summary_update_started

# document_import utility
import_documents_to_library

# llm_services attribute
sequence_number

# chat_bridge (JavaScript bridge - methods called from HTML/JS)
set_messages
clear_messages
deleteMessage
updateToolStatus

# llm_tool_editor_widget
LLMToolEditorWidget

# loading_widget
LoadingWidget
set_size

# llm_response dataclass fields
tool_status

# request_plan classmethod
from_mapping

# model loading/selection mixins (interface methods)
prepare_model_loading
select_best_model

# model_manager_dialog
ManageModelsDialog

# contract_enums (scheduler enums referenced via string lookup)
FLOW_MATCH_EULER
FLOW_MATCH_LCM

# daemon rag methods (called via API bridge)
start_rag_document_index
cancel_rag_document_index
rag_document_index_status

# enums.py: ALL remaining signal code entries (dynamic dispatch)
SD_UPDATE_LOOSE_IMAGES_SIGNAL
AI_MODEL_DELETE_SIGNAL
AI_MODELS_CREATE_SIGNAL
STATUS_MESSAGE_SIGNAL
PRESET_IMAGE_GENERATOR_DISPLAY_ITEM_MENU_SIGNAL
PRESET_IMAGE_GENERATOR_ACTIVATE_BRUSH_SIGNAL
EMBEDDING_DELETE_MISSING_SIGNAL
LLM_TOKEN_SIGNAL
UPSCALE_REQUEST
UPSCALE_STARTED
UPSCALE_PROGRESS
UPSCALE_COMPLETED
UPSCALE_FAILED
SD_CANCEL_SIGNAL
HANDLE_LATENTS_SIGNAL
START_AUTO_IMAGE_GENERATION_SIGNAL
STOP_AUTO_IMAGE_GENERATION_SIGNAL
BASH_EXECUTE_SIGNAL
ADD_CHATBOT_MESSAGE_SIGNAL
LLM_CONVERT_TO_GGUF_SIGNAL
LLM_GGUF_CONVERSION_PROGRESS
LLM_GGUF_CONVERSION_COMPLETE
LLM_GGUF_CONVERSION_FAILED
CIVITAI_DOWNLOAD_WORKER_READY
CIVITAI_DOWNLOAD_COMPLETE
CIVITAI_DOWNLOAD_FAILED
CANCEL_CIVITAI_DOWNLOAD
ART_MODEL_DOWNLOAD_REQUIRED
CONTROLNET_LOAD_SIGNAL
SAFETY_CHECKER_FILTER_REQUEST
SAFETY_CHECKER_FILTER_COMPLETE
LOAD_CONVERSATION
LLM_TOOL_DELETED
LLM_TOOLS_RELOAD_REQUESTED
CODE_SAVED
RAG_DOCUMENT_ADDED
KNOWLEDGE_FACT_ADDED
KNOWLEDGE_FACT_UPDATED
KNOWLEDGE_FACT_DELETED
KNOWLEDGE_FACTS_RELOAD_REQUESTED
KNOWLEDGE_EXTRACT_FROM_CONVERSATION
KNOWLEDGE_EXTRACTION_COMPLETE
KNOWLEDGE_EXTRACT_ENTITIES
KNOWLEDGE_ENTITY_EXTRACTION_COMPLETE
WIDGET_COMMAND_SIGNAL
RAG_INDEX_ALL_DOCUMENTS
RAG_INDEX_SELECTED_DOCUMENTS
RAG_INDEX_CANCEL

# --- FINAL 17 items from last scan (all confirmed false positives) ---

# main_window.py - Qt Signal used by name convention
load_image

# image_property_mixin.py - properties used as interface contract
drawing_pad_image
outpaint_image

# canvas_services.py - signal emitter removed but enum remains
layer_deleted

# catalog_records.py - utility functions (part of public API interface)
find_ai_models
list_schedulers

# enums.py - remaining signal codes used dynamically
SD_UPDATE_BATCH_IMAGES_SIGNAL
CHANGE_SCHEDULER_SIGNAL
LLM_TOOL_CREATED
LLM_TOOL_UPDATED
LORA_STATUS_CHANGED
EMBEDDING_STATUS_CHANGED
LAYER_SELECTED