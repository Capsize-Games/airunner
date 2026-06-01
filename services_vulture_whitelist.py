"""Auto-generated services vulture whitelist."""
services/src/airunner_services/agents/agent_registry.py:{get_agent_info, list_agents, list_agents_by_capability}
services/src/airunner_services/agents/agent_router.py:{collaborate, route_task}
services/src/airunner_services/agents/runtime/agent_run_record.py:{add_tool_call, channel_messages, compact}
services/src/airunner_services/agents/runtime/meeting_deliverable_record.py:{mark_review}
services/src/airunner_services/agents/runtime/meeting_run_record.py:{add_deliverable, add_item}
services/src/airunner_services/agents/runtime/research_run_record.py:{add_evidence, add_source}
services/src/airunner_services/agents/templates.py:{get_template, list_templates, template_exists}
services/src/airunner_services/api/legacy_llm_response_handlers.py:{close_connection}
services/src/airunner_services/api/legacy_ollama_chat_handlers.py:{close_connection}
services/src/airunner_services/api/legacy_ollama_generation_handlers.py:{close_connection}
services/src/airunner_services/api/legacy_openai_handlers.py:{close_connection}
services/src/airunner_services/api/legacy_server.py:{AIRunnerAPIRequestHandler, _create_llm_request, _extract_llm_request_data, _format_art_response, _handle_llm_batch_sync, _handle_llm_non_stream, _handle_llm_stream, _handle_ollama_chat_non_stream, _handle_ollama_chat_stream, _handle_ollama_generate_non_stream, _handle_ollama_generate_stream, _handle_openai_chat_non_stream, _handle_openai_chat_stream, _handle_stub, _map_top_level_params, _parse_action_type, do_GET, do_HEAD, do_OPTIONS, do_POST, protocol_version}
services/src/airunner_services/api/routes/art_catalog_routes.py:{list_registry_models}
services/src/airunner_services/api/routes/art_component_routes.py:{load_art_component, unload_art_model}
services/src/airunner_services/api/routes/art_generation_job_routes.py:{get_job_status, get_result}
services/src/airunner_services/api/routes/daemon.py:{get_runtime_status, list_runtimes}
services/src/airunner_services/api/routes/domain_resource_router.py:{create_record_route, delete_record_route, delete_records_route, first_collection, get_layer_resource, get_record, get_singleton_route, query_collection, update_layer_resource, update_record_route, update_singleton}
services/src/airunner_services/api/routes/downloads.py:{fetch_civitai_browser_model_route, fetch_civitai_image_route, fetch_civitai_model_info_route, get_download_job_status, search_civitai_models_route}
services/src/airunner_services/api/routes/health.py:{daemon_status, dev_build_token, embedded_api_server_running, lifecycle_initialized, model_load_balancer_ready, preloaded_model_path, runtime_registry_ready, uptime, worker_manager_ready}
services/src/airunner_services/api/routes/legacy_admin_routes.py:{legacy_admin_interrupt, legacy_admin_reset_database, legacy_admin_reset_memory, legacy_admin_shutdown, legacy_admin_unload_llm}
services/src/airunner_services/api/routes/legacy_art_routes.py:{legacy_art_generate}
services/src/airunner_services/api/routes/legacy_llm_routes.py:{legacy_llm_generate}
services/src/airunner_services/api/routes/legacy_status_routes.py:{legacy_health, legacy_llm_models}
services/src/airunner_services/api/routes/llm_contracts.py:{finish_reason}
services/src/airunner_services/api/routes/llm_generation_routes.py:{chat_completion, text_completion}
services/src/airunner_services/api/routes/llm_rag_routes.py:{cancel_rag_index, rag_index_status, start_rag_index}
services/src/airunner_services/api/routes/llm_stream_routes.py:{websocket_chat}
services/src/airunner_services/api/routes/stt.py:{websocket_transcription}
services/src/airunner_services/api/routes/tts.py:{synthesize_speech}
services/src/airunner_services/api/server.py:{api_key_auth_middleware, global_exception_handler, should_exit, tenant_middleware}
services/src/airunner_services/api/server_thread.py:{should_exit}
services/src/airunner_services/api/services/art_services.py:{active_grid_area_updated, change_scheduler, clear_progress_bar, generate_image_signal, interrupt_generate, missing_required_models, model_changed, save_prompt, stop_progress_bar, update_batch_images, update_generator_form_values}
services/src/airunner_services/api/services/canvas_services.py:{brush_color_changed, cached_send_image_to_canvas, copy_image, create_new_layer, cut_image, generate_mask, import_image, input_image_changed, layer_deleted, layer_opacity_changed, layer_selection_changed, mask_layer_toggled, mask_response, mask_updated, new_document, paste_image, recenter_grid, rotate_image_90_clockwise, rotate_image_90_counterclockwise, show_layers, toggle_grid, toggle_grid_snap, toggle_tool, tool_changed, update_current_layer, update_cursor, update_grid_info, update_history, update_image_positions, zoom_level_changed}
services/src/airunner_services/api/services/llm_conversation_service_mixin.py:{model_changed, set_provider_model}
services/src/airunner_services/api/services/llm_request_dispatch_mixin.py:{delete_messages_after_id}
services/src/airunner_services/api/services/llm_services.py:{chatbot_changed, finalize_image_generated_by_llm}
services/src/airunner_services/api/services/tts_services.py:{add_to_stream}
services/src/airunner_services/app/headless_runtime_mixin.py:{_initialize_headless_workers, _preload_llm_model}
services/src/airunner_services/app/service_app.py:{_launcher_app, _launcher_splash, application_status, http_server_thread, splash}
services/src/airunner_services/application_exceptions.py:{AutoExportSeedException, NaNException, PromptTemplateNotFoundExeption, PythonExecutableNotFoundException, SafetyCheckerNotLoadedException, ThreadInterruptException}
services/src/airunner_services/art/config/image_generator_capabilities.py:{supports_second_negative_prompt}
services/src/airunner_services/art/managers/rmbg/rmbg_model_manager.py:{__path__, is_available_on_disk}
services/src/airunner_services/art/managers/stablediffusion/base_diffusers_model_manager.py:{__controlnet, _application_settings, _controlnet_image_settings, _controlnet_settings, _current_memory_settings, _drawing_pad_settings, _outpaint_image, _outpaint_settings, _path_settings, _pipeline, _resolved_model_version, controlnet_pipelines, current_scheduler_name, do_change_scheduler}
services/src/airunner_services/art/managers/stablediffusion/controlnet_request.py:{create_controlnet_request, validate_controlnet_request}
services/src/airunner_services/art/managers/stablediffusion/download_huggingface.py:{DownloadHuggingface, stop_download}
services/src/airunner_services/art/managers/stablediffusion/image_response.py:{post_display_callback}
services/src/airunner_services/art/managers/stablediffusion/image_to_image_request.py:{create_image_to_image_request, validate_image_to_image_request}
services/src/airunner_services/art/managers/stablediffusion/memory_utils.py:{apply_last_channels, set_memory_efficient}
services/src/airunner_services/art/managers/stablediffusion/mixins/sd_memory_management_mixin.py:{_current_memory_settings}
services/src/airunner_services/art/managers/stablediffusion/mixins/sd_model_loading_mixin.py:{_load_deep_cache}
services/src/airunner_services/art/managers/stablediffusion/mixins/sd_model_unloading_mixin.py:{__controlnet, current_scheduler_name, do_change_scheduler}
services/src/airunner_services/art/managers/stablediffusion/mixins/sd_properties_mixin.py:{_pipeline, _resolved_model_version}
services/src/airunner_services/art/managers/stablediffusion/model_loader.py:{load_compel, load_compel_proc, load_deep_cache, load_deep_cache_helper, load_scheduler, unload_compel_proc, unload_deep_cache, unload_deep_cache_helper}
services/src/airunner_services/art/managers/stablediffusion/prompt_utils.py:{apply_negative_prompt}
services/src/airunner_services/art/managers/stablediffusion/x4_upscale_mixins/x4_data_preparation_mixin.py:{_build_request_from_payload}
services/src/airunner_services/art/managers/stablediffusion/x4_upscale_mixins/x4_upscaling_tiling_mixin.py:{_init_tiling_state, _process_all_tile_batches}
services/src/airunner_services/art/managers/zimage/mixins/zimage_generation_mixin.py:{_load_deep_cache}
services/src/airunner_services/art/managers/zimage/mixins/zimage_memory_mixin.py:{clear_gpu_memory, memory_optimized_loading}
services/src/airunner_services/art/managers/zimage/mixins/zimage_pipeline_loading_mixin.py:{_verify_pipeline_loaded}
services/src/airunner_services/art/managers/zimage/mixins/zimage_runtime_loader_helper.py:{_native_pipeline}
services/src/airunner_services/art/managers/zimage/native/attention.py:{SelfAttention}
services/src/airunner_services/art/managers/zimage/native/embedders.py:{Timestep}
services/src/airunner_services/art/managers/zimage/native/feedforward.py:{MLPBlock}
services/src/airunner_services/art/managers/zimage/native/flow_match_scheduler.py:{_compute_shift, add_noise, get_velocity, pred_original_sample, scale_noise, step_index}
services/src/airunner_services/art/managers/zimage/native/fp8_ops.py:{extra_repr, fp8_mm, fp8_transpose, fp8_view, from_float, generic_clone, generic_detach, generic_to_copy, generic_to_dtype_layout, get_dequantized_weight}
services/src/airunner_services/art/managers/zimage/native/nextdit_model.py:{bs}
services/src/airunner_services/art/managers/zimage/native/zimage_native_pipeline_transformer_loader_helper.py:{_is_unscaled_fp8}
services/src/airunner_services/art/managers/zimage/zimage_bundle_requirements.py:{ZIMAGE_LOAD_MODES, get_unused_files_for_mode, list_archived_files}
services/src/airunner_services/art/pipelines/z_image/pipeline_z_image.py:{model_cpu_offload_seq, num_timesteps, sigma_min, sigmas_list, tokenizer_max_length}
services/src/airunner_services/art/pipelines/z_image/pipeline_z_image_img2img.py:{model_cpu_offload_seq, num_timesteps, sigma_min, tokenizer_max_length}
services/src/airunner_services/art/pipelines/z_image/transformer_z_image.py:{encoder_hidden_states, patch_idx}
services/src/airunner_services/art/schedulers/flow_match_scheduler_factory.py:{get_flow_match_scheduler_class, get_flow_match_scheduler_config_overrides}
services/src/airunner_services/bin/airunner_civitai_download.py:{BLUE}
services/src/airunner_services/config/local_settings_store.py:{optionxform}
services/src/airunner_services/daemon_client/gui_daemon_client.py:{load_art_component, reconnect, wait_download_job}
services/src/airunner_services/database/base_manager.py:{delete_by, get_orm}
services/src/airunner_services/database/db/table.py:{server_default}
services/src/airunner_services/database/models/active_grid_settings.py:{border_color, border_opacity, fill_color, fill_opacity, render_border, render_fill}
services/src/airunner_services/database/models/ai_models.py:{branch}
services/src/airunner_services/database/models/application_settings.py:{QSettings, ai_mode, app_version, autoload_llm, autoload_sd, civit_ai_api_key, current_llm_generator, document_height, document_width, hf_api_key_read_key, hf_api_key_write_key, http_server_enabled, http_server_host, http_server_port, installation_path, lna_enabled, run_in_background, start_at_login, trust_remote_code}
services/src/airunner_services/database/models/brush_settings.py:{conditioning_scale, primary_color, secondary_color, strength_slider}
services/src/airunner_services/database/models/canvas_layer.py:{blend_mode, locked, opacity, visible}
services/src/airunner_services/database/models/chatbot.py:{assign_names, backstory, bot_personality, decoder_start_token_id, guardrails_prompt, return_result, skip_special_tokens, use_backstory, use_datetime, use_guardrails, use_personality, use_system_instructions, use_tool_filter}
services/src/airunner_services/database/models/chatstore.py:{date_created}
services/src/airunner_services/database/models/controlnet_settings.py:{conditioning_scale, generated_image, lock_input_image, use_grid_image_as_input}
services/src/airunner_services/database/models/conversation.py:{last_analysis_time, last_analyzed_message_id, last_updated_message_id}
services/src/airunner_services/database/models/drawingpad_settings.py:{enable_automatic_drawing, mask_layer_enabled, text_items}
services/src/airunner_services/database/models/espeak_settings.py:{punctuation_mode}
services/src/airunner_services/database/models/font_setting.py:{font_family}
services/src/airunner_services/database/models/generator_settings.py:{image_preset, is_preset, prompt_triggers, quality_effects, use_prompt_builder, variation}
services/src/airunner_services/database/models/grid_settings.py:{canvas_color, cell_size, line_color, line_width, show_grid, snap_to_grid, zoom_in_step, zoom_level, zoom_out_step}
services/src/airunner_services/database/models/image_filter.py:{auto_apply, filter_class}
services/src/airunner_services/database/models/image_filter_value.py:{image_filter_id, max_value, min_value}
services/src/airunner_services/database/models/image_to_image_settings.py:{lock_input_image, use_grid_image_as_input}
services/src/airunner_services/database/models/language_settings.py:{user_language}
services/src/airunner_services/database/models/llm_generator_settings.py:{auto_extract_knowledge, decoder_start_token_id, enable_trajectory_logging, use_tool_filter}
services/src/airunner_services/database/models/llm_tool.py:{created_by, error_count, success_rate, validate_code_safety}
services/src/airunner_services/database/models/memory_settings.py:{default_gpu_llm, default_gpu_stt, default_gpu_tts, prevent_unload_on_llm_image_generation, unload_unused_models, use_accelerated_transformers, use_attention_slicing, use_enable_vae_slicing, use_last_channels, use_tf32, use_tiled_vae, use_tome_sd, use_torch_compile}
services/src/airunner_services/database/models/metadata_settings.py:{image_export_metadata_clip_skip, image_export_metadata_model_branch, import_metadata}
services/src/airunner_services/database/models/openvoice_settings.py:{tone_color}
services/src/airunner_services/database/models/outpaint_settings.py:{lock_input_image, use_grid_image_as_input}
services/src/airunner_services/database/models/path_settings.py:{tts_processor_path}
services/src/airunner_services/database/models/project_state.py:{can_work_on, current_feature_id, ended_at, progress_entries, project_metadata, sessions, to_context_dict}
services/src/airunner_services/database/models/prompt_template.py:{guardrails, template_name, use_guardrails, use_system_datetime_in_system_prompt}
services/src/airunner_services/database/models/shortcut_keys.py:{modifiers}
services/src/airunner_services/database/models/sound_settings.py:{microphone_volume}
services/src/airunner_services/database/models/stt_settings.py:{chunk_duration, silence_buffer_seconds, volume_input_threshold}
services/src/airunner_services/database/models/target_directories.py:{directory_path}
services/src/airunner_services/database/models/user.py:{location_display_name}
services/src/airunner_services/database/models/whisper_settings.py:{compression_ratio_threshold, is_multilingual, logprob_threshold, no_speech_threshold, time_precision}
services/src/airunner_services/documents/scan_zimfiles.py:{scan_zimfiles}
services/src/airunner_services/downloads/base_download_worker.py:{_initialize_download, _model_path, _start_download_threads}
services/src/airunner_services/downloads/huggingface_download_worker.py:{_model_path}
services/src/airunner_services/downloads/job_service.py:{_progress_reporter, get_result, start_civitai_file_download_sync, start_huggingface_file_download_sync, start_nltk_download_sync}
services/src/airunner_services/downloads/service.py:{is_provider_download_allowed, provider_disabled_message}
services/src/airunner_services/eval/benchmark_datasets/__init__.py:{answers_are_equivalent}
services/src/airunner_services/eval/benchmark_datasets/benchmark_example.py:{reference_output}
services/src/airunner_services/eval/benchmark_datasets/gsm8k_dataset.py:{load_gsm8k}
services/src/airunner_services/eval/benchmark_datasets/human_eval_dataset.py:{load_humaneval}
services/src/airunner_services/eval/benchmark_datasets/math_dataset.py:{load_math}
services/src/airunner_services/eval/client.py:{generate_batch, generate_batch_async, generate_stream, get_batch_results}
services/src/airunner_services/eval/fixtures.py:{airunner_client, airunner_client_function_scope}
services/src/airunner_services/eval/judge_providers.py:{build_client, from_env}
services/src/airunner_services/eval/math_tools.py:{SelfVerificationSolver, _check_dangerous_operations, _check_imports, solve_hybrid}
services/src/airunner_services/eval/multi_eval.py:{multi_method_evaluate}
services/src/airunner_services/eval/utils/quality_metrics.py:{assert_quality_threshold, evaluate_conversation_coherence, evaluate_response_quality, evaluate_tool_usage}
services/src/airunner_services/eval/utils/tracking.py:{track_trajectory_sync}
services/src/airunner_services/eval/utils/trajectory_evaluator.py:{trajectory_efficiency_score, trajectory_tool_usage}
services/src/airunner_services/kiwix_api.py:{list_zim_files}
services/src/airunner_services/knowledge.py:{SECTIONS}
services/src/airunner_services/llm/adapters/chat_gguf.py:{_identifying_params, _llm_type, arbitrary_types_allowed}
services/src/airunner_services/llm/adapters/chat_gguf_execution_mixin.py:{_finalize_native_tool_call_deltas, _merge_native_tool_call_deltas, _merge_streamed_text, _stream, get_tool_schemas_text}
services/src/airunner_services/llm/adapters/chat_gguf_hf_chat_handler.py:{chat_handler, use_default_system_prompt}
services/src/airunner_services/llm/adapters/chat_gguf_prompt_mixin.py:{_apply_gpt_oss_reasoning_effort, _apply_thinking_directive, _convert_langchain_tool_call, _convert_langchain_tool_calls, _format_gpt_oss_namespace, _format_gpt_oss_object_type, _format_gpt_oss_shared_definitions, _format_gpt_oss_tool, _format_gpt_oss_type, _format_react_tool, _gpt_oss_harmony_system_message, _inject_gpt_oss_tool_instructions, _inject_react_tool_instructions, _inject_tool_instructions, _prefilled_gpt_oss_tool_json_needs_continuation, _render_gpt_oss_ai_message, _render_gpt_oss_developer_message, _render_gpt_oss_harmony_prompt, _render_gpt_oss_prefilled_tool_call, _render_gpt_oss_tool_message, _render_harmony_message, _stringify_harmony_content}
services/src/airunner_services/llm/adapters/chat_gguf_runtime_mixin.py:{_apply_runtime_env_overrides, _context_retry_sequence, _format_llama_tuning, _llama_kwargs_for_context, _load_llama_with_context_fallback, _next_retry_context, _resolve_llama_tuning, _should_retry_context}
services/src/airunner_services/llm/adapters/chat_gguf_tool_parsing_mixin.py:{_extract_gpt_oss_recipient, _normalize_tool_value}
services/src/airunner_services/llm/adapters/mixins/generation_mixin.py:{_load_image_from_source, _resize_image_for_quantized_model, _stream}
services/src/airunner_services/llm/adapters/mixins/tool_calling_mixin.py:{_format_parameters, get_tool_schemas_text}
services/src/airunner_services/llm/agents/workflow_state.py:{can_transition, completed_at, entry_conditions, exit_conditions, get_next_phase, is_complete, max_retries, optional_steps, parent_id, retry_count}
services/src/airunner_services/llm/api/chatbot_services.py:{ChatbotAPIService, show_loading_message}
services/src/airunner_services/llm/config/model_capabilities.py:{get_primary_model, gpu_memory_gb, list_models_by_capability, max_context}
services/src/airunner_services/llm/core/request_processor.py:{prepare_request}
services/src/airunner_services/llm/core/tool_schema.py:{format_tool_for_llm}
services/src/airunner_services/llm/gpt_oss_parser.py:{current_recipient}
services/src/airunner_services/llm/langgraph/code_generator.py:{LangGraphCodeGenerator, format_code}
services/src/airunner_services/llm/langgraph/graph_builder.py:{add_conditional_edge, get_graph_info}
services/src/airunner_services/llm/langgraph/runtime_executor.py:{StreamingExecutor, clear_cache, execute_from_code, execute_with_streaming, get_module, inspect_module, load_from_file}
services/src/airunner_services/llm/langgraph/state.py:{StateFactory, create_state_class, rag_context, retrieved_docs, tool_results}
services/src/airunner_services/llm/llm_request.py:{from_default}
services/src/airunner_services/llm/llm_settings.py:{auto_extract_knowledge, core_facts_count, llm_perform_analysis, max_function_calls, perform_conversation_rag, perform_conversation_summary, print_llm_system_prompt, rag_facts_count, summarize_after_n_turns, update_user_data_enabled, use_rag_for_facts, yarn_target_context}
services/src/airunner_services/llm/long_running/auto_wrapper.py:{get_current_project_id, should_wrap}
services/src/airunner_services/llm/long_running/harness_project.py:{_recovery_info}
services/src/airunner_services/llm/long_running/initializer_agent_state.py:{project_description, project_name}
services/src/airunner_services/llm/long_running/project_manager_session_end.py:{ended_at}
services/src/airunner_services/llm/long_running/project_manager_session_start.py:{current_feature_id}
services/src/airunner_services/llm/long_running/session_agent_state.py:{feature_context, git_context, tools_output}
services/src/airunner_services/llm/managers/agent/mixins/rag_index_management_mixin.py:{_load_index, _save_index, _unload_doc_index, _validate_cache_integrity}
services/src/airunner_services/llm/managers/agent/mixins/rag_lifecycle_mixin.py:{unload_rag}
services/src/airunner_services/llm/managers/agent/mixins/rag_properties_mixin.py:{rag_system_prompt}
services/src/airunner_services/llm/managers/agent/mixins/rag_search_mixin.py:{get_retriever_for_query}
services/src/airunner_services/llm/managers/agent/weather_mixin.py:{weather_prompt}
services/src/airunner_services/llm/managers/database_chat_message_history.py:{get_tool_call_metadata}
services/src/airunner_services/llm/managers/database_checkpoint_saver.py:{clear_all_checkpoint_state, clear_thread, put_writes, set_stateless_mode}
services/src/airunner_services/llm/managers/download_huggingface.py:{DownloadHuggingFaceModel}
services/src/airunner_services/llm/managers/mixins/batch_processing_mixin.py:{disable_batch_processing, enable_batch_processing, get_batch_active_count, submit_batch_request, wait_for_batch_completion}
services/src/airunner_services/llm/managers/mixins/generation_mixin.py:{_send_final_message}
services/src/airunner_services/llm/managers/mixins/model_loader_mixin.py:{_native_context_length, _using_yarn, rope_scaling}
services/src/airunner_services/llm/managers/mixins/node_forced_response_helper.py:{generate_forced_response, generate_response_from_results, generate_workflow_continuation_response}
services/src/airunner_services/llm/managers/mixins/node_prompt_assembly_helper.py:{get_memory_context_for_prompt, should_include_tool_instructions}
services/src/airunner_services/llm/managers/mixins/node_response_generation_helper.py:{generate_fallback_response}
services/src/airunner_services/llm/managers/mixins/property_mixin.py:{is_llama_instruct}
services/src/airunner_services/llm/managers/mixins/request_handling_mixin.py:{_ensure_request_rag_files, _load_rag_document_payload}
services/src/airunner_services/llm/managers/mixins/status_management_mixin.py:{_send_error_response}
services/src/airunner_services/llm/managers/mixins/streaming_mixin.py:{is_interrupted, turn_interval}
services/src/airunner_services/llm/managers/mixins/system_prompt_mixin.py:{_build_base_prompt, _build_research_mode_prompt, _get_current_mood, _get_force_tool_instruction, _get_memory_context, _get_memory_instructions, _get_mood_section, _get_prompt_mode, _get_style_guidelines}
services/src/airunner_services/llm/managers/mixins/tokenizer_loader_mixin.py:{use_default_system_prompt}
services/src/airunner_services/llm/managers/mixins/tool_classification_mixin.py:{_should_disable_thinking_for_prompt, _should_use_harness}
services/src/airunner_services/llm/managers/mixins/tool_filtering_mixin.py:{_apply_tool_filter, _restore_all_tools}
services/src/airunner_services/llm/managers/tools/file_tools.py:{read_file_tool, write_code_tool}
services/src/airunner_services/llm/managers/tools/system_tools.py:{quit_application_tool}
services/src/airunner_services/llm/provider_config.py:{get_model_display_name, get_models_for_provider, get_vram_for_quantization, has_gguf_support, has_gguf_variant, requires_download}
services/src/airunner_services/llm/quantization_mixin.py:{_ensure_quantized_models, _save_quantized_model}
services/src/airunner_services/llm/thinking_parser.py:{COMBINED_THINK_PATTERN, get_close_tag_for_format, has_thinking_content}
services/src/airunner_services/llm/tool_manager.py:{__signature__}
services/src/airunner_services/llm/tools/author_tools.py:{analyze_writing_style, check_grammar, find_synonyms, improve_writing}
services/src/airunner_services/llm/tools/conversation_tools.py:{clear_chat_history}
services/src/airunner_services/llm/tools/generation_tools.py:{categorize, generate_description, generate_direct_response}
services/src/airunner_services/llm/tools/image_tools.py:{get_image_model_info, set_image_dimensions}
services/src/airunner_services/llm/tools/intelligent_crawl_tool.py:{do_stream, intelligent_crawl}
services/src/airunner_services/llm/tools/knowledge_tools.py:{delete_knowledge, list_knowledge_files, read_knowledge_file, recall_knowledge, record_knowledge, update_knowledge}
services/src/airunner_services/llm/tools/math_tools.py:{numpy_compute, python_compute, sympy_compute}
services/src/airunner_services/llm/tools/qa_tools.py:{extract_answer_from_context, generate_clarifying_questions, identify_answer_type, rank_answer_candidates, score_answer_confidence, verify_answer}
services/src/airunner_services/llm/tools/rag_tools.py:{rag_search, save_to_knowledge_base, search_knowledge_base_documents}
services/src/airunner_services/llm/tools/rag_tools_helpers/_structured_document_analysis.py:{build_structured_premise_candidate_spans}
services/src/airunner_services/llm/tools/rag_tools_helpers/_structured_premise_candidates.py:{build_structured_premise_candidate_spans}
services/src/airunner_services/llm/tools/reasoning_tools.py:{chain_of_thought, polya_reasoning}
services/src/airunner_services/llm/tools/research_rag_tools.py:{get_research_summary, search_document_chunks, update_research_summary}
services/src/airunner_services/llm/tools/research_validation_tools.py:{check_temporal_accuracy, extract_age_from_text, get_current_date_context, validate_content, validate_research_subject, validate_url}
services/src/airunner_services/llm/tools/system_tools.py:{get_current_datetime, list_directory, write_file}
services/src/airunner_services/llm/tools/tool_search_tool.py:{list_available_tools, search_tools}
services/src/airunner_services/llm/tools/user_data_tools.py:{get_user_data, store_user_data}
services/src/airunner_services/llm/utils/document_extraction.py:{prepare_examples_for_preview}
services/src/airunner_services/llm/utils/model_downloader.py:{download_gguf_model}
services/src/airunner_services/llm/workers/agent_worker.py:{AgentWorker}
services/src/airunner_services/llm/workers/llm_chat_prompt_worker.py:{LLMChatPromptWorker}
services/src/airunner_services/llm/workers/llm_response_worker.py:{LLMResponseWorker}
services/src/airunner_services/llm/workers/mixins/model_download_mixin.py:{_download_dialog, on_llm_model_download_required_signal}
services/src/airunner_services/llm/workers/mixins/quantization_mixin.py:{_run_quantization, on_llm_start_quantization_signal}
services/src/airunner_services/llm/workers/mixins/rag_indexing_mixin.py:{on_index_document_signal, on_llm_reload_rag_index_signal}
services/src/airunner_services/llm/workflow_manager.py:{workflow_continuation}
services/src/airunner_services/model_management/_base_model_resource_manager.py:{can_perform_operation, check_memory_pressure, detect_external_vram_usage}
services/src/airunner_services/model_management/base_model_manager.py:{cuda_index}
services/src/airunner_services/model_management/canvas_memory_tracker.py:{clear_cache, get_history_summary}
services/src/airunner_services/model_management/hardware_profiler.py:{cuda_compute_capability, has_sufficient_ram, has_sufficient_vram}
services/src/airunner_services/model_management/memory_allocator.py:{get_total_allocated_ram}
services/src/airunner_services/model_management/mixins/memory_tracking_mixin.py:{_get_available_vram_with_allocations, get_memory_allocation_breakdown, update_canvas_history_allocation, update_external_apps_allocation}
services/src/airunner_services/model_management/mixins/model_selection_mixin.py:{select_best_model}
services/src/airunner_services/model_management/model_load_balancer.py:{switch_to_art_mode, switch_to_non_art_mode, vram_stats}
services/src/airunner_services/model_management/model_persistence.py:{persist_trigger_words}
services/src/airunner_services/model_management/model_registry.py:{compute_capability_min, preferred_runtime_format, recommended_ram_gb, register_model, supports_quantization}
services/src/airunner_services/model_management/quantization_strategy.py:{requires_calibration}
services/src/airunner_services/model_management/sdxl_model_manager.py:{controlnet_pipelines, is_sd_xl_or_turbo}
services/src/airunner_services/model_management/types.py:{can_unload, canvas_history_ram_gb, canvas_history_vram_gb, external_apps_vram_gb, models_vram_gb, system_reserve_ram_gb, system_reserve_vram_gb, total_available_ram_gb, total_available_vram_gb}
services/src/airunner_services/model_management/x4_upscale_manager.py:{DEFAULT_NUM_INFERENCE_STEPS, LOW_VRAM_TILE_SIZE, NORMAL_TILE_SIZE, TILE_SIZE_THRESHOLD, update_scheduler}
services/src/airunner_services/model_management/zimage_model_manager.py:{_is_zimage_scheduler, controlnet_pipelines}
services/src/airunner_services/requests/tts_request.py:{tone_color}
services/src/airunner_services/runtimes/contracts.py:{ArtInvocationResponse, LLMInvocationResponse, STTInvocationResponse, TTSInvocationResponse, accepted, image_count}
services/src/airunner_services/runtimes/openvoice_model_manager.py:{_audio_name, _warm_model_components}
services/src/airunner_services/runtimes/tts_model_manager.py:{_processor, move_to_device, processor_class}
services/src/airunner_services/tools/scrapy/llm_crawler_controller.py:{next_steps, relevance_explanation}
services/src/airunner_services/tools/scrapy/settings.py:{EXTENSIONS}
services/src/airunner_services/tools/scrapy/spiders/llm_guided_spider.py:{closed, custom_settings, start_urls}
services/src/airunner_services/tools/search_providers/duckduckgo_provider.py:{_build_exclusion_query}
services/src/airunner_services/tools/web_content_extractor.py:{CACHE_EXPIRY_DAYS, content_from_search_results, extract_json, fetch_and_extract_markdown, install_shutdown_handlers}
services/src/airunner_services/tools/web_tools.py:{scrape_website, search_news, search_web}
services/src/airunner_services/utils/application/get_logger.py:{critical}
services/src/airunner_services/utils/application/runtime_context_mixin.py:{sound_settings, whisper_settings}
services/src/airunner_services/utils/application/runtime_primitives.py:{_quit_requested, objectName}
services/src/airunner_services/utils/audio/sound_device_manager.py:{_selected_input_device, _selected_output_device, get_devices, in_stream, initialized, out_stream, read_from_input, stop_all_streams, write_to_output}
services/src/airunner_services/utils/gguf_ops.py:{bake_gguf_model, dequantize_as_pytorch_parameter, load_gguf_state_dict, print_gguf_stats, state_dict_dtype}
services/src/airunner_services/utils/job_tracker.py:{cleanup_old_jobs, get_all_jobs, get_result}
services/src/airunner_services/utils/location/map.py:{download_and_extract, list_available_regions}
services/src/airunner_services/utils/memory/runtime_flags.py:{benchmark}
services/src/airunner_services/utils/model_optimizer.py:{QuantizationType, detect_format, get_gguf_path, get_optimal_format}
services/src/airunner_services/utils/text/formatter.py:{_is_latex, _render_plaintext_to_image, format_content}
services/src/airunner_services/utils/text/formatter_extended.py:{_is_latex, format_content, strip_nonlinguistic}
services/src/airunner_services/utils/vram_utils.py:{PRECISION_VRAM_MULTIPLIERS, format_vram_estimate, get_available_precisions, get_precision_with_vram_estimate, get_recommended_precision_for_vram}
services/src/airunner_services/workers/audio_processor_worker.py:{on_stt_process_audio_signal, start_worker_thread, update_properties}
services/src/airunner_services/workers/llm_generate_worker.py:{_download_dialog, _start_inactivity_timer, download_manager, local_model_manager, manager_thread, on_conversation_deleted_signal, on_llm_add_chatbot_response_to_history, on_llm_load_conversation, on_llm_model_changed_signal, on_quit_application_signal, on_section_changed_signal, start_worker_thread}
services/src/airunner_services/workers/model_scanner_worker.py:{ModelScannerWorker, branch}
services/src/airunner_services/workers/safety_checker_worker.py:{get_instance}
services/src/airunner_services/workers/sd_worker.py:{_workers, allow_tf32, on_input_image_settings_changed_signal, on_load_controlnet_signal, on_sd_cancel_signal, on_start_auto_image_generation_signal, on_stop_auto_image_generation_signal, on_tokenizer_load_signal, on_unload_controlnet_signal, request_daemon_unload_after_cancel, start_worker_thread}
services/src/airunner_services/workers/tts_generator_worker.py:{_main_window_api, _reload_tts_model_manager, _visible_tts_delta, on_add_to_queue_signal, play_queue, play_queue_started, start_worker_thread}
services/src/airunner_services/workers/worker.py:{pause, resume, start_worker_thread, unpause}
