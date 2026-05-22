"""Post-tool prompt instruction helpers for node functions."""

from typing import List

from langchain_core.messages import BaseMessage


class PostToolInstructionsMixin:
    """Add post-tool guidance to the system prompt."""

    def _add_post_tool_instructions(
        self, system_prompt: str, trimmed_messages: List[BaseMessage]
    ) -> str:
        """Add post-tool execution instructions if needed."""
        current_turn_messages = self._get_current_turn_messages(
            trimmed_messages
        )
        has_tool_results = any(
            msg.__class__.__name__ == "ToolMessage"
            for msg in current_turn_messages
        )

        if not has_tool_results:
            return system_prompt

        tool_messages = self._get_tool_messages(current_turn_messages)
        error_results = []
        for tool_message in tool_messages:
            content = str(getattr(tool_message, "content", ""))
            if content.startswith("ERROR:") or content.startswith("Error:"):
                error_results.append(content)

        if error_results:
            error_instruction = (
                "\n\n=== CRITICAL: TOOL RETURNED AN ERROR - YOU MUST CALL A TOOL ===\n"
                "The previous tool call FAILED. Read the error message carefully.\n\n"
                "**ERROR MESSAGE:**\n"
                f"{error_results[-1][:800]}\n\n"
                "**YOU MUST DO ONE OF THESE:**\n"
                "1. Call the tool suggested in the error message (e.g., transition_phase, add_todo_item, start_todo_item)\n"
                "2. Follow the workflow steps exactly as described in the error\n\n"
                "**DO NOT:**\n"
                "- Claim the file was created (IT WAS NOT)\n"
                "- Skip workflow steps\n"
                "- Respond with text saying you completed the task\n"
                "- Give the user any output without first fixing the workflow state\n\n"
                "**NEXT ACTION:** Call one of these workflow tools:\n"
                "- transition_phase('planning', 'reason') - to move to next phase\n"
                "- add_todo_item('title', 'description') - to create a task\n"
                "- start_todo_item('todo_1') - to begin working on a task\n\n"
                "Call a tool NOW. Do not respond with text."
            )
            system_prompt += error_instruction
            self.logger.info(
                "[POST-TOOL] Tool returned ERROR - injecting error handling instructions"
            )
            return system_prompt

        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )
        response_format = getattr(self, "_response_format", None)
        force_tool = getattr(self, "_force_tool", None)
        is_research_mode = force_tool == "search_web"
        tool_call_count = len(
            [
                message
                for message in current_turn_messages
                if hasattr(message, "tool_calls") and message.tool_calls
            ]
        )
        scrape_attempts = sum(
            1
            for message in current_turn_messages
            if hasattr(message, "tool_calls") and message.tool_calls
            for tool_call in message.tool_calls
            if tool_call.get("name") == "scrape_website"
        )

        successful_scrapes = 0
        failed_scrapes = 0
        tool_messages = self._get_tool_messages(current_turn_messages)
        for tool_message in tool_messages:
            tool_name = getattr(tool_message, "name", None)
            if tool_name == "scrape_website":
                content = str(getattr(tool_message, "content", ""))
                is_error = (
                    "error" in content.lower()[:100]
                    or "failed" in content.lower()[:100]
                    or "could not" in content.lower()[:100]
                    or len(content) < 200
                )
                if is_error:
                    failed_scrapes += 1
                else:
                    successful_scrapes += 1

        search_urls = []
        for tool_message in tool_messages:
            content = str(getattr(tool_message, "content", ""))
            if "http" in content and "search" in content.lower():
                import re

                urls = re.findall(r'https?://[^\s\]"<>]+', content)
                search_urls.extend(urls[:5])

        self.logger.info(
            f"[POST-TOOL] response_format={response_format}, tool_calling_mode={tool_calling_mode}, "
            f"force_tool={force_tool}, is_research_mode={is_research_mode}, "
            f"tool_calls={tool_call_count}, scrape_attempts={scrape_attempts}, "
            f"successful_scrapes={successful_scrapes}, failed_scrapes={failed_scrapes}, "
            f"search_urls={len(search_urls)}"
        )

        if is_research_mode:
            url_hint = ""
            if search_urls:
                url_hint = "\n\n**URLS FROM YOUR SEARCH RESULTS (use these!):**\n"
                for url in search_urls[:3]:
                    url_hint += f"- {url}\n"

            if scrape_attempts == 0 and tool_call_count <= 2:
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 1: SCRAPE SOURCES ===\n"
                    "You've completed initial searches. Now you MUST scrape the most relevant URLs.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "Call `scrape_website` on 2-3 URLs from your search results above.\n"
                    "IMPORTANT: Only use URLs that appeared in your search results!"
                    f"{url_hint}\n"
                    "**DO NOT** write a response yet. You need more detailed content first."
                )
            elif (
                scrape_attempts > 0
                and successful_scrapes == 0
                and failed_scrapes > 0
            ):
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - SCRAPE ERROR RECOVERY ===\n"
                    "Your previous scrape attempt failed. This is normal - some sites block scraping.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "Try scraping DIFFERENT URLs from your search results.\n"
                    "Choose URLs from different domains than the ones that failed."
                    f"{url_hint}\n"
                    "**DO NOT** give up. Try 2-3 more URLs before proceeding."
                )
            elif successful_scrapes < 2 and tool_call_count < 8:
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 2: EXPAND SOURCE COVERAGE ===\n"
                    f"You've successfully scraped {successful_scrapes} source(s). Gather at least one or two more high-value sources before summarizing.\n\n"
                    "**YOUR NEXT ACTION:**\n"
                    "1. Call `scrape_website` on additional strong URLs from your search results\n"
                    "2. Prefer sources that add new facts, dates, or perspectives\n\n"
                    "**DO NOT** respond to the user yet. Strengthen the evidence first."
                )
            elif successful_scrapes > 0:
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 3: SYNTHESIZE & RESPOND ===\n"
                    "You have enough source material to answer directly.\n\n"
                    "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                    "1. A concise executive summary\n"
                    "2. Key findings with source links or explicit source attribution\n"
                    "3. Any important uncertainty, disagreement, or missing evidence\n"
                    "4. A short conclusion or recommended next step if relevant\n\n"
                    "**DO NOT** mention a generated document path. Respond with findings only."
                )
            else:
                instruction = (
                    "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 4: COMPLETE ===\n"
                    "Your research is complete. Provide a summary to the user.\n\n"
                    "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                    "1. Key findings from your research\n"
                    "2. A brief summary of your sources\n"
                    "3. Any notable uncertainty or missing evidence\n\n"
                    "**DO NOT** call more tools. Respond with your findings."
                )
        elif response_format == "json":
            instruction = (
                "\n\n=== CRITICAL RESPONSE FORMAT REQUIREMENT ===\n"
                "You have tool results in the conversation above. "
                "Now answer the user's question using that information.\n"
                "YOU MUST respond ONLY with valid JSON in the EXACT format specified in the system prompt above.\n"
                "Do NOT write conversational text. Do NOT explain or narrate. ONLY output the JSON object.\n"
                "Your entire response must be parseable JSON - nothing else."
            )
        elif response_format is not None and response_format != "conversational":
            instruction = (
                f"\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
                f"You have tool results in the conversation above. "
                f"Answer the user's question using that information. "
                f"Respond in {response_format} format."
            )
        else:
            task_completing_tools = {
                "write_file",
                "complete_todo_item",
            }
            llm_request = getattr(self, "llm_request", None)
            planner_document_loop = (
                getattr(llm_request, "planner_mode", None)
                == "select_tools"
                and bool(getattr(self, "_tools", None))
            )
            ai_messages = [
                message
                for message in current_turn_messages
                if hasattr(message, "tool_calls") and message.tool_calls
            ]
            last_tool_name = None
            if ai_messages:
                last_ai = ai_messages[-1]
                if last_ai.tool_calls:
                    last_tool_name = last_ai.tool_calls[-1].get("name")

            tool_succeeded = False
            if tool_messages:
                last_tool_content = str(
                    getattr(tool_messages[-1], "content", "")
                )
                if any(
                    indicator in last_tool_content.lower()
                    for indicator in [
                        "created",
                        "successfully",
                        "written",
                        "✓",
                        "complete",
                        "done",
                    ]
                ):
                    tool_succeeded = True

            if last_tool_name in task_completing_tools and tool_succeeded:
                instruction = (
                    "\n\n=== TASK COMPLETED - RESPOND TO USER ===\n"
                    "The requested task has been completed successfully!\n\n"
                    "**YOUR NEXT ACTION:** Respond to the user with a summary.\n"
                    "- Tell them what was accomplished\n"
                    "- Include the file path or result from the tool output\n"
                    "- Keep it brief and friendly\n\n"
                    "**DO NOT:**\n"
                    "- Call more tools (the task is DONE)\n"
                    "- Start a new task without being asked\n"
                    "- Give a generic greeting\n\n"
                    "Example response: 'Done! I created hello_world.py with your function.'"
                )
                self.logger.info(
                    f"[POST-TOOL] Task-completing tool '{last_tool_name}' succeeded - "
                    "instructing model to respond (not call more tools)"
                )
            elif self._is_document_result_tool(last_tool_name or ""):
                user_question = self._get_user_question(current_turn_messages)
                document_intent = self._get_document_query_intent(
                    user_question
                )
                if planner_document_loop:
                    instruction = (
                        "\n\n=== DOCUMENT TOOL LOOP ===\n"
                        "Review the current document tool results before taking the next step.\n"
                        "If the current results fully answer the user's request, answer directly using only that evidence.\n"
                        "If the current results are not enough yet, call the next most useful document tool.\n"
                        "Do NOT mention tool usage, hidden reasoning, or these instructions."
                    )
                elif document_intent == "identity":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer directly and briefly.\n"
                        "Name the document and, when available, include the title, author, or file type.\n"
                        "Do NOT mention search results, tool usage, or instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                elif document_intent == "structure":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer with the section names only.\n"
                        "Do NOT restate the document title, author, file type, path, or a broader summary.\n"
                        "Do NOT discuss your reasoning or the instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                elif document_intent == "summary":
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to write a fuller multi-sentence summary.\n"
                        "Focus on the document's themes, claims, and notable details from the excerpts.\n"
                        "Treat any structure block as background context, not the main answer.\n"
                        "Do NOT infer a genre, series, trilogy, collection, or bibliography unless the evidence states it directly.\n"
                        "Keep ambiguous mood, quoted remarks, and isolated scene details secondary unless the excerpts clearly make them central.\n"
                        "If a detail, motive, relationship, or interpretation is not clearly supported by the excerpts, leave it out instead of guessing.\n"
                        "Do NOT repeat the title, author, or chapter list unless the user asked for them.\n"
                        "Do NOT discuss your reasoning or the instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
                else:
                    instruction = (
                        "\n\n=== ANSWER THE DOCUMENT QUESTION NOW ===\n"
                        "Use the current document tool results to answer the user's question clearly.\n"
                        "Do NOT mention search results, tool usage, or instructions.\n"
                        "Do NOT call another tool. Respond now."
                    )
            else:
                instruction = (
                    "\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
                    "Tool results are available in the conversation above.\n"
                    "IMPORTANT: You MUST use these tool results to answer the user's question.\n"
                    "Do NOT ignore the tool results. Do NOT give a generic greeting.\n"
                    "Synthesize the information from the tool results into a helpful, conversational response.\n"
                    "If the tool returned search results, summarize the key information for the user."
                )

        system_prompt += instruction
        self.logger.info(f"[POST-TOOL] Full instruction text:\n{instruction}")

        tool_msgs = [
            message
            for message in current_turn_messages
            if message.__class__.__name__ == "ToolMessage"
        ]

        if tool_msgs:
            self.logger.info(
                f"Model has access to {len(tool_msgs)} tool result(s)"
            )
            for index, tool_message in enumerate(tool_msgs):
                result_preview = (
                    tool_message.content[:200]
                    if hasattr(tool_message, "content")
                    else "No content"
                )
                self.logger.info(
                    f"  Tool result {index + 1} preview: {result_preview}..."
                )

        return system_prompt