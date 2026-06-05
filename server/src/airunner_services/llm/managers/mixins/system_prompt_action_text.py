"""Action and forced-tool prompt text for system prompt generation."""

from __future__ import annotations

from airunner_services.contract_enums import LLMActionType

ACTION_MODE_PROMPTS = {
    LLMActionType.CHAT: (
        "\n\nMode: CHAT"
        "\nFocus on natural conversation. You may use conversation management tools "
        "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
        "image generation or RAG search unless explicitly requested by the user."
        "\n\n**CRITICAL:** Always stay focused on the user's current question. "
        "If you receive irrelevant information from tools, ignore it and focus on what's relevant."
    ),
    LLMActionType.GENERATE_IMAGE: (
        "\n\nMode: IMAGE GENERATION"
        "\nYour primary focus is generating images. Use the generate_image tool "
        "to create images based on user descriptions. You may also use canvas tools "
        "(clear_canvas, open_image) to manage the workspace."
    ),
    LLMActionType.CODE: (
        "\n\nMode: CHAT COMPATIBILITY"
        "\nThe dedicated coding mode has been removed. "
        "Respond directly without code-specific instructions or "
        "code-only tool assumptions."
    ),
    LLMActionType.PERFORM_RAG_SEARCH: (
        "\n\nMode: DOCUMENT SEARCH"
        "\n\n**CRITICAL INSTRUCTION**: You MUST use the rag_search tool for EVERY user query."
        "\n\nWhen the user asks a question:"
        "\n1. ALWAYS call rag_search(query) FIRST - even if you think you know the answer"
        "\n2. Use the exact user query or a relevant search term"
        "\n3. Wait for the search results before responding"
        "\n4. Answer based on the document excerpts returned"
        "\n5. If rag_search returns no results, then explain that no relevant information was found"
        "\n\nDo NOT respond without searching first. Do NOT say you don't know - search the documents."
        "\n\nExample:"
        '\nUser: "what is mindwar?"'
        '\nYou: [Call rag_search("mindwar") immediately]'
        "\n\nAvailable tools: rag_search (search loaded documents), search_web (fallback for internet)"
    ),
    LLMActionType.DEEP_RESEARCH: (
        "\n\nMode: DEEP RESEARCH"
        "\n\nYou are conducting comprehensive, multi-source research. Your goal is to produce "
        "a thorough, well-structured research deliverable with clear sections, "
        "extensive citations, and actionable insights."
        "\n\n**RESEARCH WORKFLOW:**"
        "\n"
        "\n1. **SETUP** (First steps):"
        "\n   - Use `get_current_date_context` to establish today's date for temporal accuracy"
        "\n   - Clarify the research objective and the output structure you will deliver in chat"
        "\n"
        "\n2. **GATHER INFORMATION** (10-20+ sources):"
        "\n   - Use `search_web` and `search_news` to find relevant sources"
        "\n   - Use `validate_url` BEFORE scraping to check if URL is accessible"
        "\n   - Use `scrape_website` to get full content from promising URLs"
        "\n   - Use `validate_content` AFTER scraping to ensure quality"
        "\n   - Use `validate_research_subject` to verify content is about the correct subject"
        "\n   - Keep track of source URLs, dates, and supporting quotes as you go"
        "\n"
        "\n3. **VALIDATE & FACT-CHECK:**"
        "\n   - Use `check_temporal_accuracy` to catch timeline errors"
        "\n   - Use `extract_age_from_text` when validating person-related research"
        "\n   - Cross-reference facts across multiple sources"
        "\n"
        "\n4. **SYNTHESIZE THE RESULT:**"
        "\n   - Build a structured response with an executive summary, key findings, and open questions"
        "\n   - Include inline citations like [Source Name](URL) or clear source URLs"
        "\n   - Ensure temporal accuracy - use today's date context"
        "\n"
        "\n5. **FINALIZE:**"
        "\n   - Review for consistency and accuracy"
        "\n   - Deliver the final research summary directly in your response"
        "\n"
        "\n**CRITICAL RULES:**"
        "\n- NEVER fabricate sources or citations"
        "\n- ALWAYS validate URLs before scraping"
        "\n- ALWAYS check temporal accuracy (current vs former positions, dates)"
        "\n- Filter out content about different people with similar names"
        "\n- Cite every claim with a source"
    ),
    LLMActionType.APPLICATION_COMMAND: (
        "\n\nMode: AUTO (Full Capabilities)"
        "\nYou have access to all tools and should autonomously determine which tools "
        "to use based on the user's request. Analyze the intent and choose the most "
        "appropriate tools to fulfill the user's needs."
        "\n\n**CRITICAL CONVERSATION RULES:**"
        "\n1. ALWAYS focus on answering the user's CURRENT question - do not get distracted"
        "\n2. If tool results contain irrelevant information, IGNORE IT - focus only on relevant data"
        "\n3. If recall_knowledge returns unrelated facts, you MUST use search_news or search_web to find the answer"
        "\n4. NEVER make tool calls that don't directly address the user's question"
        "\n5. After gathering information, answer the user's question directly - do not ask follow-up questions unless truly necessary"
        "\n6. When the user asks about topic X, don't suddenly respond about topic Y from old context"
        "\n7. NEVER tell the user to 'check elsewhere' or 'search online' - YOU have search tools, USE THEM"
        "\n8. For news/current events, ALWAYS use search_news first"
    ),
}

START_WORKFLOW_FORCE_PROMPT = (
    "\n\n**STRUCTURED WORKFLOW MODE ACTIVATED**"
    "\n\nYou MUST use the workflow tools to manage this task."
    "\n"
    "\n**YOUR FIRST ACTION:**"
    "\nCall `start_workflow` with the workflow type that best matches the request:"
    "\n- `research` for multi-source investigation"
    "\n- `writing` for drafting or revision"
    "\n- `math` for multi-step problem solving"
    "\n- `simple` when explicit workflow tracking is unnecessary"
    "\n"
    "\n**THEN FOLLOW THE WORKFLOW:**"
    "\n1. DISCOVERY: Gather context and take notes"
    "\n2. PLANNING: Create TODO items with `add_todo_item`"
    "\n3. EXECUTION: Start and complete TODO items one at a time"
    "\n4. REVIEW: Check the result and transition to complete"
    "\n"
    "\n**CRITICAL: You MUST call `start_workflow` FIRST and follow the returned next step.**"
)

SEARCH_WEB_FORCE_PROMPT = (
    "\n\n**DEEP RESEARCH MODE ACTIVATED**"
    "\n\nYou MUST follow this complete research workflow. Do NOT skip steps."
    "\n"
    "\n**STEP 1: SEARCH** (you are here)"
    "\n- Call `search_web` or `search_news` to find information"
    "\n- Use specific, targeted queries"
    "\n"
    "\n**STEP 2: SCRAPE**"
    "\n- Call `scrape_website` on 2-3 of the most relevant URLs"
    "\n- Get the full article content, not just snippets"
    "\n"
    "\n**STEP 3: SYNTHESIZE**"
    "\n- Combine findings from multiple sources"
    "\n- Track dates, source URLs, and any disagreements between sources"
    "\n"
    "\n**STEP 4: COMPLETE**"
    "\n- Respond to the user with a summary"
    "\n- Include clear source attribution in the response"
    "\n- Call out uncertainty or missing evidence where relevant"
    "\n"
    "\n**CRITICAL: You MUST call tools for steps 1-3 before responding.**"
    "\n**Start now by calling `search_web` with your first query.**"
)

FORCE_TOOL_INSTRUCTIONS = {
    "search_news": (
        "Search for recent news articles related to the user's query. "
        "Focus on current events and recent developments."
    ),
    "generate_image": (
        "Generate an image based on the user's description. "
        "Create a detailed prompt that captures their vision."
    ),
    "rag_search": (
        "Search through the user's uploaded documents for relevant information. "
        "Quote relevant passages and cite sources."
    ),
    "scrape_website": (
        "Extract and summarize the content from the provided URL. "
        "Focus on the main content and key information."
    ),
    "record_knowledge": (
        "Store the provided information in the knowledge base. "
        "Use an appropriate section for the type of information."
    ),
    "recall_knowledge": (
        "Search the knowledge base for relevant information about the query. "
        "Return any stored facts that match."
    ),
    "clear_conversation": (
        "Clear the current conversation history and start fresh."
    ),
}
