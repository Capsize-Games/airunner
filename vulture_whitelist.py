"""Auto-generated vulture whitelist."""
src/airunner/__init__.py:{_torchao_version}
src/airunner/api/api_bridge.py:{ensure_connected, is_connected}
src/airunner/app_installer.py:{do_show_setup_wizard}
src/airunner/app_mixins/ui_runtime_mixin.py:{is_running}
src/airunner/components/agents/agent_registry.py:{get_agent_info, list_agents, list_agents_by_capability}
src/airunner/components/agents/agent_router.py:{collaborate, route_task}
src/airunner/components/agents/runtime/agent_run_record.py:{add_tool_call, channel_messages, compact}
src/airunner/components/agents/runtime/meeting_deliverable_record.py:{mark_review}
src/airunner/components/agents/runtime/meeting_run_record.py:{add_deliverable, add_item}
src/airunner/components/agents/runtime/research_run_record.py:{add_evidence, add_source}
src/airunner/components/agents/templates.py:{template_exists}
src/airunner/components/application/api/api.py:{_initialize_app, clear_download_status, click_me_button, connect_signal, llm_model_download_progress, quit_application, send_image_request, set_download_progress, set_download_status, show_dynamic_ui, worker_response}
src/airunner/components/application/data/__init__.py:{class_names, table_to_class}
src/airunner/components/application/gui/dialogs/privacy_consent_dialog.py:{is_duckduckgo_allowed, is_openai_allowed, is_openrouter_allowed}
src/airunner/components/application/gui/widgets/base_widget.py:{clear_status_message_text, get_is_checked, get_plain_text, services, set_button_icon, set_is_checked, set_plain_text, set_text, set_value, static_html_dir}
src/airunner/components/application/gui/widgets/keyboard_shortcuts/keyboard_shortcuts_widget.py:{save_shortcuts}
src/airunner/components/application/gui/widgets/paths/path_widget.py:{auto_discover}
src/airunner/components/application/gui/widgets/paths/tests/test_path_widget_functional.py:{pytestmark}
src/airunner/components/application/gui/widgets/slider/slider_widget.py:{set_display_as_float, set_label, set_maximum, set_minimum, set_step_size, set_tick_value, set_value}
src/airunner/components/application/gui/widgets/status/status_widget.py:{feature_extractor_status, safety_checker_status}
src/airunner/components/application/gui/windows/main/ai_model_mixin.py:{ai_model_categories, ai_model_get_disabled_default, ai_model_paths, ai_model_pipeline_actions, ai_model_versions, ai_models_find}
src/airunner/components/application/gui/windows/main/base_mixin.py:{BaseMixin, get_all, get_by_filter}
src/airunner/components/application/gui/windows/main/embedding_mixin.py:{EmbeddingMixin, delete_missing_embeddings}
src/airunner/components/application/gui/windows/main/main_window.py:{_action_new_shortcut, _configured_runtime_resource_model_id, _document_path, _generate_drawingpad_mask, _generator, _generator_settings, _gui_probe_controller, _knowledgebase_panel_is_visible, _restore_tab, _set_current_button_and_tab, _set_tab_index, _themes, _updating_settings, action_show_model_path_txt2img, bash_execute, button_clicked_signal, deterministic_window, generator_tab_changed_signal, handle_double_click, handle_unknown, header_widget_spacer, image_generated, input_event_manager, key_text, last_tray_click_time, load_image_object, move_to_second_screen, on_actionBrowse_Images_Path_2_triggered, on_actionReset_Settings_2_triggered, on_actionRun_setup_wizard_2_triggered, progress_bar_started, set_path_settings, show_grid_toggled, show_path, show_update_message, show_update_popup, status_error_color, status_normal_color_dark, status_normal_color_light, token_signal, tqdm_callback_triggered, update_popup, window_opened}
src/airunner/components/application/gui/windows/main/mixins/basic_settings_update_mixin.py:{update_controlnet_image_settings, update_font_setting, update_saved_prompt}
src/airunner/components/application/gui/windows/main/mixins/image_property_mixin.py:{controlnet_generated_image, drawing_pad_mask, outpaint_mask}
src/airunner/components/application/gui/windows/main/mixins/model_management_mixin.py:{add_embedding, add_lora, create_lora, delete_embedding, delete_lora, delete_lora_by_name, get_embedding_by_name, get_lora_by_name, update_loras}
src/airunner/components/application/gui/windows/main/mixins/settings_cache_mixin.py:{clear_cache_settings}
src/airunner/components/application/gui/windows/main/mixins/settings_list_property_mixin.py:{font_settings, image_filter_values, prompt_templates}
src/airunner/components/application/gui/windows/main/mixins/utility_and_chatbot_mixin.py:{get_chatbot_by_id}
src/airunner/components/application/gui/windows/main/model_load_balancer.py:{switch_to_art_mode, vram_stats}
src/airunner/components/application/gui/windows/main/pipeline_mixin.py:{available_pipeline_by_action_version_category, available_pipeline_by_section, get_pipeline_classname}
src/airunner/components/application/gui/windows/main/worker_manager.py:{_handle_image_generation_request, _handle_llm_download_directly, _llm_model_change_requires_runtime_reload, _reload_tts_model_manager, document_worker, image_export_worker, non_llm_types, update_properties}
src/airunner/components/application/managers/base_model_manager.py:{ModelManagerInterface, attn_implementation, cuda_index, flass_attn_varlen_func, handle_requested_action}
src/airunner/components/application/workers/daemon_huggingface_download_worker.py:{_active_payload}
src/airunner/components/application/workers/qt_civitai_workers.py:{_cancelled}
src/airunner/components/application/workers/worker.py:{pause, resume, start_worker_thread, unpause}
src/airunner/components/art/api/art_services.py:{clear_progress_bar, embedding_updated, final_progress_update, generate_image_signal, llm_image_generated, lora_updated, missing_required_models, pipeline_loaded}
src/airunner/components/art/api/canvas_services.py:{layer_opacity_changed, mask_layer_toggled, rotate_image_90_clockwise, rotate_image_90_counterclockwise, send_image_to_canvas}
src/airunner/components/art/config/image_generator_capabilities.py:{dimension_step, min_height, min_width, supports_second_negative_prompt}
src/airunner/components/art/data/bootstrap/imagefilter_bootstrap_data.py:{imagefilter_bootstrap_data}
src/airunner/components/art/data/canvas_layer_records.py:{all_canvas_layers, delete_canvas_layer, delete_layer_setting}
src/airunner/components/art/filters/rgb_noise.py:{blue_grain, green_grain, red_grain}
src/airunner/components/art/gui/dialogs/new_document_dialog.py:{_custom_size}
src/airunner/components/art/gui/widgets/active_grid_settings/active_grid_settings_widget.py:{ActiveGridSettingsWidget}
src/airunner/components/art/gui/widgets/canvas/batch_container.py:{BatchContainer}
src/airunner/components/art/gui/widgets/canvas/brush_scene.py:{_do_generate_image, create_line}
src/airunner/components/art/gui/widgets/canvas/canvas_layer_container_widget.py:{CanvasLayerContainerWidget}
src/airunner/components/art/gui/widgets/canvas/canvas_widget.py:{_active_grid_settings, _grid_settings, _startPos, active_grid_area_pivot_point, active_grid_area_position, current_image_index, drag_pos}
src/airunner/components/art/gui/widgets/canvas/custom_scene.py:{_create_image, _release_painter_for_device, _serialize_record, _set_current_active_image}
src/airunner/components/art/gui/widgets/canvas/custom_view.py:{_get_default_text_font}
src/airunner/components/art/gui/widgets/canvas/draggables/active_grid_area.py:{_current_height, _current_snapped_pos, _current_width, _do_draw, _line_width, _render_border, change_border_opacity, change_fill_opacity, drag_start_display_pos, fresh_settings, initial_item_abs_pos, initial_mouse_scene_pos, mouse_press_pos, toggle_render_border, toggle_render_fill}
src/airunner/components/art/gui/widgets/canvas/draggables/layer_image_item.py:{_current_snapped_pos, initial_item_abs_pos, initial_mouse_scene_pos, mouse_press_pos}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_active_image_mixin.py:{_binary_to_pil_fast}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_history_mixin.py:{_serialize_record}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_image_conversion_mixin.py:{_binary_to_pil_fast}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_image_initialization_mixin.py:{refresh_image}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_initialization_mixin.py:{_active_persist_future, _current_active_image_hash, _image_initialized, _qimage_cache_hash, _target_size, do_generate_image, do_update, generate_image_time, generate_image_time_in_ms, handling_event, selection_start_pos, selection_stop_pos}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_item_management_mixin.py:{clear_selection, selection_start_pos, selection_stop_pos}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_mouse_event_mixin.py:{do_update}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_painter_mixin.py:{_release_painter_for_device}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_persistence_mixin.py:{_active_persist_future, _handle_persist_result}
src/airunner/components/art/gui/widgets/canvas/mixins/canvas_surface_management_mixin.py:{_qimage_cache_hash}
src/airunner/components/art/gui/widgets/canvas/mixins/cursor_tool_mixin.py:{get_cached_cursor}
src/airunner/components/art/gui/widgets/canvas/mixins/initialization_mixin.py:{_editing_text_item, _scene_is_active, _temp_rubberband, _text_drag_start, _text_dragging, do_draw_layers, line_group, pixmaps}
src/airunner/components/art/gui/widgets/canvas/mixins/position_management_mixin.py:{get_layer_position}
src/airunner/components/art/gui/widgets/embeddings/embeddings_container_widget.py:{EmbeddingsContainerWidget}
src/airunner/components/art/gui/widgets/grid_preferences/grid_preferences_widget.py:{GridPreferencesWidget}
src/airunner/components/art/gui/widgets/image/image_widget.py:{ImageWidget}
src/airunner/components/art/gui/widgets/lora/lora_container_widget.py:{LoraContainerWidget, handle_lora_slider, handle_lora_spinbox, initialize_lora_trigger_words}
src/airunner/components/art/gui/widgets/stablediffusion/stable_diffusion_settings_widget.py:{FLOW_MATCH_SCHEDULER_NAME}
src/airunner/components/art/gui/widgets/stablediffusion/stablediffusion_generator_form.py:{changed_signal, do_generate_image, extract_json_from_message, get_memory_options, is_txt2img, seed_override, unload_llm_callback}
src/airunner/components/art/gui/windows/filter_list_window/filter_list_window.py:{_on_item_changed}
src/airunner/components/art/gui/windows/filter_window/filter_window.py:{image_filter_model_name}
src/airunner/components/art/managers/rmbg/rmbg_model_manager.py:{__path__, is_available_on_disk, remove_background_to_png_bytes}
src/airunner/components/art/managers/stablediffusion/download_huggingface.py:{DownloadHuggingface}
src/airunner/components/art/managers/stablediffusion/image_request.py:{control_guidance_end, control_guidance_start, controlnet_guess_mode, lora_scale, outpaint_mask_blur}
src/airunner/components/art/managers/stablediffusion/memory_utils.py:{apply_last_channels, get_hardware_profiler, set_memory_efficient}
src/airunner/components/art/managers/stablediffusion/model_loader.py:{SomeEmbeddingsClass, load_compel, load_compel_proc, load_controlnet, load_controlnet_model, load_controlnet_processor, load_deep_cache, load_deep_cache_helper, load_embedding, load_scheduler, unload_compel_proc, unload_controlnet_processor, unload_deep_cache, unload_deep_cache_helper, unload_embeddings, unload_lora}
src/airunner/components/art/managers/stablediffusion/utils.py:{resize_image}
src/airunner/components/art/managers/zimage/zimage_bundle_requirements.py:{ZIMAGE_LOAD_MODES, find_active_checkpoint, get_downloadable_files_for_mode, get_missing_files_for_mode, get_unused_files_for_mode, list_archived_files}
src/airunner/components/art/trainers/base.py:{_global_step_to_epoch, image_column, lora_alpha, lora_dropout, lora_rank, lora_target_modules, lr_warmup_steps, num_train_epochs, save_precision, train_text_encoder}
src/airunner/components/art/utils/canvas_position_manager.py:{get_centered_position}
src/airunner/components/art/utils/image_filter_utils.py:{get_all_filter_names}
src/airunner/components/art/utils/layer_compositor.py:{create_layer_from_image, get_layer_bounds}
src/airunner/components/art/utils/nsfw_checker.py:{check_and_mark_nsfw_images}
src/airunner/components/art/utils/safetensors_inspector.py:{get_file_type, should_download_text_encoders, should_download_vae}
src/airunner/components/chat/gui/widgets/chat_prompt_widget.py:{_active_section, _clear_document_attachments, _clear_image_attachments, _collect_images_for_llm, _disabled, _ensure_history_view_loaded, _ensure_settings_view_loaded, _find_parent_tab_widget, _get_model_capabilities, _highlighted, _llm_history_tab_index, _llm_history_widget, _llm_response_worker, _on_submit_shortcut, _prompt_submit_shortcuts, _remove_image_attachment, _set_conversation_widgets, action_menu_displayed, add_message_to_conversation, attached_document_capabilities, attached_document_total_characters, attached_document_total_tokens, display_action_menu, hide_action_menu, insert_newline, llm_action_changed, message_type_text_changed, messages_spacer, prompt_rect, register_web_channel, scroll_animation, scroll_bar, thinking_toggled}
src/airunner/components/chat/gui/widgets/conversation_widget.py:{_orphaned_tokens, _render_startup_placeholder, _restore_tool_statuses, _view, add_message_to_conversation, conversation_history, scroll_to_bottom, wait_for_dom_ready}
src/airunner/components/conversations/conversation_record.py:{user_id}
src/airunner/components/data/tenant.py:{reset_tenant_key, reset_tenant_schema_prefix, set_tenant_key, set_tenant_schema_prefix, tenant_schema_for_key}
src/airunner/components/documents/document_import.py:{is_chat_image_path}
src/airunner/components/documents/gui/widgets/documents.py:{_expand_available_document_sections, _favicon, _filter_file_explorer_extensions, _private, _request_index_for_unindexed_documents, faviconChanged, handle_drop_on_documents_table, orig_filterAcceptsRow, show_active_doc_context_menu, show_available_doc_context_menu, show_unavailable_doc_context_menu, titleChanged, urlChanged}
src/airunner/components/documents/gui/widgets/kiwix_widget.py:{show_local_zims_only}
src/airunner/components/documents/gui/widgets/knowledge_base_panel_widget.py:{_current, _document_name, _total}
src/airunner/components/downloader/gui/windows/download_wizard/download_wizard_window.py:{show_final_page}
src/airunner/components/downloader/gui/windows/setup_wizard/age_restriction/age_restriction_warning.py:{age_restriction_agreed, read_age_restriction_agreement, read_agreement_clicked}
src/airunner/components/downloader/gui/windows/setup_wizard/installation_settings/choose_models_page.py:{_core_toggled}
src/airunner/components/downloader/gui/windows/setup_wizard/installation_settings/install_page.py:{CONTROLNET_PATHS, _check_completion_fallback, _openvoice_unidic_complete, _process_next_openvoice_zip, _tts_download_in_progress, files_in_current_step, n_, steps_completed, total_attempted_files, total_failed, total_steps, total_success}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/controlnet/controlnet_setup.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/llm_welcome_screen.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/metadata_setup.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stable_diffusion_setup/choose_model.py:{using_custom_model}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stable_diffusion_setup/stable_diffusion_license.py:{setting_key}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stable_diffusion_setup/stable_diffusion_welcome_screen.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stt_welcome_screen.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/tts_welcome_screen.py:{toggled_no, toggled_yes}
src/airunner/components/downloader/gui/windows/setup_wizard/privacy_policy/privacy_policy.py:{isComplete, setting_key}
src/airunner/components/downloader/gui/windows/setup_wizard/setup_wizard_window.py:{age_restriction_warning_id, controlnet_download_id, final_page_id, llm_welcome_page_id, meta_data_settings_id, set_page_order, stable_diffusion_license_id, stt_welcome_page_id, tts_welcome_page_id, user_agreement_id, welcome_page_id}
src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/agreement_page.py:{isComplete, setting_key}
src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/user_agreement.py:{setting_key}
src/airunner/components/file_explorer/gui/widgets/file_explorer_widget.py:{_delete_item, _file_open_slot, connect_signal, set_project_service}
src/airunner/components/knowledge/knowledge_base.py:{SECTIONS, delete_fact, get_context, read_all, read_file, search_rag, update_fact}
src/airunner/components/llm/api/llm_services.py:{completion_tokens, delete_messages_after_id, prompt_tokens, visible_text}
src/airunner/components/llm/config/generation_presets.py:{apply_to_generation_kwargs}
src/airunner/components/llm/config/model_capabilities.py:{get_primary_model, gpu_memory_gb, list_models_by_capability, max_context, supports_function_calling}
src/airunner/components/llm/config/provider_config.py:{requires_download}
src/airunner/components/llm/core/code_sandbox.py:{create_safe_builtins}
src/airunner/components/llm/core/request_processor.py:{prepare_request}
src/airunner/components/llm/data/bootstrap/prompt_templates_bootstrap_data.py:{prompt_templates_bootstrap_data}
src/airunner/components/llm/gui/widgets/bot_preferences.py:{_selected_agent_type_key, toggle_use_image_generator}
src/airunner/components/llm/gui/widgets/contentwidgets/chat_bridge.py:{append_message, copyMessage, copyText, newChat, request_scroll, updateModelLoadStatus, updateThinkingStatus, update_content_height, update_last_message_content}
src/airunner/components/llm/gui/widgets/generator_form/generator_form_widget.py:{changed_signal, extract_json_from_message, get_memory_options, handle_image_presets_changed, handle_interrupt_button_clicked, is_txt2img, seed_override}
src/airunner/components/llm/gui/widgets/llm_settings_widget.py:{_hide_model_provider_controls, _toggle_model_path_visibility, download_manager, model_text_changed, set_tab, toggle_leave_model_in_vram, toggle_move_model_to_cpu, toggle_unload_model}
src/airunner/components/llm/gui/widgets/model_selector_widget.py:{ModelSelectorWidget}
src/airunner/components/llm/managers/agent/mixins/rag_document_mixin.py:{_get_active_document_names, _get_active_document_paths}
src/airunner/components/llm/managers/agent/mixins/rag_index_management_mixin.py:{_load_index, _save_index, _unload_doc_index, _validate_cache_integrity}
src/airunner/components/llm/managers/agent/mixins/rag_indexing_mixin.py:{_last_rag_index_error, _rag_retry_after_download, index_all_documents}
src/airunner/components/llm/managers/agent/mixins/rag_lifecycle_mixin.py:{clear_rag_documents, load_bytes_into_rag, load_html_into_rag}
src/airunner/components/llm/managers/agent/mixins/rag_properties_mixin.py:{rag_system_prompt}
src/airunner/components/llm/managers/agent/mixins/rag_search_mixin.py:{get_retriever_for_query}
src/airunner/components/llm/managers/agent/weather_mixin.py:{weather_prompt}
src/airunner/components/llm/managers/database_chat_message_history.py:{add_messages, get_tool_call_metadata}
src/airunner/components/llm/managers/database_checkpoint_saver.py:{clear_all_checkpoint_state, clear_checkpoints, clear_thread, put_writes, set_stateless_mode}
src/airunner/components/llm/managers/llm_request.py:{OpenrouterMistralRequest, attached_document_capabilities, attached_document_total_characters, attached_document_total_tokens, document_primary_tool, final_system_prompt, from_default, preprocessed_primary_tool, rewritten_prompt, to_debug_metadata}
src/airunner/components/llm/managers/llm_response.py:{completion_tokens, prompt_tokens, tool_arguments}
src/airunner/components/llm/managers/llm_settings.py:{LLMSettings, auto_extract_knowledge, core_facts_count, llm_perform_analysis, max_function_calls, ollama_base_url, ollama_model, openai_model, perform_conversation_rag, perform_conversation_summary, rag_facts_count, summarize_after_n_turns, update_mood_after_n_turns, update_user_data_enabled, use_api, use_chatbot_mood, use_local_llm, use_rag_for_facts, use_yarn, yarn_target_context}
src/airunner/components/llm/managers/quantization_mixin.py:{QuantizationMixin, _ensure_quantized_models, _get_quantization_info, _quantization_config, _save_quantized_model}
src/airunner/components/llm/managers/request_plan.py:{from_mapping}
src/airunner/components/llm/utils/document_extraction.py:{prepare_examples_for_preview}
src/airunner/components/llm/utils/document_query_routing.py:{route_document_query}
src/airunner/components/llm/utils/gpt_oss_parser.py:{looks_like_tool_argument_payload, raw_response}
src/airunner/components/llm/utils/language.py:{detect_language}
src/airunner/components/llm/utils/model_downloader.py:{download_gguf_model}
src/airunner/components/llm/utils/thinking_parser.py:{COMBINED_THINK_PATTERN, get_close_tag_for_format, has_thinking_content, parse_thinking_from_tokens, parse_thinking_response, raw_response}
src/airunner/components/model_management/canvas_memory_tracker.py:{clear_cache, get_history_summary}
src/airunner/components/model_management/hardware_profiler.py:{cuda_compute_capability, has_sufficient_ram, has_sufficient_vram}
src/airunner/components/model_management/memory_allocator.py:{get_total_allocated_ram}
src/airunner/components/model_management/mixins/memory_tracking_mixin.py:{_get_available_vram_with_allocations, get_memory_allocation_breakdown, update_external_apps_allocation}
src/airunner/components/model_management/mixins/model_state_mixin.py:{model_busy, model_ready}
src/airunner/components/model_management/model_registry.py:{compute_capability_min, preferred_runtime_format, recommended_ram_gb, register_model, size_mb, supports_quantization}
src/airunner/components/model_management/model_resource_manager.py:{check_memory_pressure, detect_external_vram_usage}
src/airunner/components/model_management/quantization_strategy.py:{requires_calibration}
src/airunner/components/model_management/types.py:{canvas_history_ram_gb, canvas_history_vram_gb, external_apps_vram_gb, models_vram_gb, system_reserve_ram_gb, system_reserve_vram_gb, total_available_ram_gb, total_available_vram_gb}
src/airunner/components/server/local_http_server.py:{allow_reuse_address, do_DELETE, do_HEAD, do_OPTIONS, do_POST, do_PUT, list_directory}
src/airunner/components/settings/data/bootstrap/font_settings_bootstrap_data.py:{font_settings_bootstrap_data}
src/airunner/components/settings/gui/widgets/model_manager_dialog.py:{download_failed, set_download_progress}
src/airunner/components/settings/gui/widgets/model_selector_widget.py:{ModelSelectorWidget, get_model_id, get_provider, set_model, set_provider}
src/airunner/components/settings/gui/widgets/sound_settings/sound_settings_widget.py:{adjust_input_level, monitoring, update_microphone_volume}
src/airunner/components/settings/gui/windows/settings/airunner_settings.py:{add_selected_index, get_callback_for_slider, remove_selected_index}
src/airunner/components/stt/api/stt_services.py:{audio_processor_response}
src/airunner/components/stt/executors/whisper_local_executor.py:{_sampling_rate, audio_stream, stt_is_failed}
src/airunner/components/stt/gui/widgets/stt_settings_widget.py:{STTSettingsWidget}
src/airunner/components/stt/workers/audio_capture_worker.py:{_audio_process_queue, overflowed}
src/airunner/components/tts/api/tts_services.py:{add_to_stream, play_audio, toggle}
src/airunner/components/tts/gui/widgets/open_voice_preferences_widget.py:{speed_changed}
src/airunner/components/tts/workers/tts_generator_worker.py:{_llm_spoken_visible_text}
src/airunner/components/tts/workers/tts_vocalizer_worker.py:{handle_speech, reader_mode_active}
src/airunner/daemon_client/gui_daemon_client.py:{health_check}
src/airunner/daemon_client/resource_store.py:{is_layer_resource}
src/airunner/dev_build_token.py:{current_dev_build_token}
src/airunner/enums.py:{CodeOperationType, Controlnet, FilterType, HandlerState, QualityEffects, Quantize}
src/airunner/gui/utils/ui_dispatcher.py:{test_hello_world_window}
src/airunner/linux_bundle_layout.py:{build_linux_bundle_layout, daemon_executable, path_environment}
src/airunner/qt_runtime_env.py:{prefers_software_qt_rendering}
src/airunner/runtime_layout.py:{as_environment, ensure_exists}
src/airunner/runtimes/runtime_layout.py:{as_environment, ensure_exists}
src/airunner/test_support/gui_harness.py:{emitted_signals, headless}
src/airunner/utils/application/background_worker.py:{update_status}
src/airunner/utils/application/logging_utils.py:{_get_log_level_from_env, _setup_file_logging, log_method_entry_exit}
src/airunner/utils/application/mediator_mixin.py:{unregister_signals}
src/airunner/utils/application/signal_mediator.py:{unregister_pending_request, wait_for_response}
src/airunner/utils/application/threaded_worker_mixin.py:{ThreadedWorkerMixin, execute_in_background, get_active_background_tasks, stop_all_background_tasks}
src/airunner/utils/audio/sound_device_manager.py:{_selected_input_device, _selected_output_device, get_devices, stop_all_streams}
src/airunner/utils/gguf_ops.py:{bake_gguf_model, dequantize_as_pytorch_parameter, load_gguf_state_dict, print_gguf_stats, state_dict_dtype}
src/airunner/utils/image/convert_binary_to_image.py:{snippet}
src/airunner/utils/location/map.py:{download_and_extract, list_available_regions}
src/airunner/utils/memory/runtime_flags.py:{benchmark}
src/airunner/utils/models/scan_path_for_items.py:{versionfiles, versionnames}
src/airunner/utils/text/formatter.py:{_is_latex, _render_plaintext_to_image}
src/airunner/utils/text/formatter_extended.py:{_is_latex}
