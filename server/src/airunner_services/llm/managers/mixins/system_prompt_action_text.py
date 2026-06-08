"""Action and forced-tool prompt text for system prompt generation."""

from __future__ import annotations

from airunner_services.contract_enums import LLMActionType

ACTION_MODE_PROMPTS = {
    LLMActionType.CHAT: (
        "\n\nMode: CHAT"
        "\nFocus on natural conversation. You may use conversation management tools "
        "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
        "image generation or RAG search unless explicitly requested by the user."
        "\n\nStay focused on the user's current question. "
        "If you receive irrelevant information from tools, set it aside and focus on what's relevant."
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
        "\n\nGuidelines: Prefer using the rag_search tool for user queries when documents are loaded."
        "\n\nWhen the user asks a question:"
        "\n1. Call rag_search(query) first — use the user's query or a relevant search term"
        "\n2. Answer based on the document excerpts returned"
        "\n3. If rag_search returns no results, explain that no relevant information was found"
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
        "\n**Guidelines:**"
        "\n- Do not fabricate sources or citations"
        "\n- Validate URLs before scraping when possible"
        "\n- Check temporal accuracy (current vs former positions, dates)"
        "\n- Filter out content about different people with similar names"
        "\n- Cite claims with a source when available"
    ),
    LLMActionType.APPLICATION_COMMAND: (
        "\n\nMode: AUTO (Full Capabilities)"
        "\nYou have access to all tools and should autonomously determine which tools "
        "to use based on the user's request. Analyze the intent and choose the most "
        "appropriate tools to fulfill the user's needs."
        "\n\n**Guidelines:**"
        "\n1. Focus on answering the user's current question"
        "\n2. If tool results contain irrelevant information, skip it and focus on relevant data"
        "\n3. If recall_knowledge returns unrelated facts, prefer search_news or search_web to find the answer"
        "\n4. Avoid tool calls that don't directly address the user's question"
        "\n5. After gathering information, answer the user's question directly"
        "\n6. Stay focused on the current topic rather than carrying over old context"
        "\n7. For news/current events, prefer search_news first"
    ),
}

START_WORKFLOW_FORCE_PROMPT = (
    "\n\n**STRUCTURED WORKFLOW MODE**"
    "\n\nUse the workflow tools to manage this task."
    "\n"
    "\n**First action:**"
    "\nCall `start_workflow` with the workflow type that best matches the request:"
    "\n- `research` for multi-source investigation"
    "\n- `writing` for drafting or revision"
    "\n- `math` for multi-step problem solving"
    "\n- `simple` when explicit workflow tracking is unnecessary"
    "\n"
    "\n**Workflow phases:**"
    "\n1. DISCOVERY: Gather context and take notes"
    "\n2. PLANNING: Create TODO items with `add_todo_item`"
    "\n3. EXECUTION: Start and complete TODO items one at a time"
    "\n4. REVIEW: Check the result and transition to complete"
)

SEARCH_WEB_FORCE_PROMPT = (
    "\n\n**DEEP RESEARCH MODE**"
    "\n\nResearch workflow to follow:"
    "\n"
    "\n**Step 1: Search**"
    "\n- Call `search_web` or `search_news` with specific, targeted queries"
    "\n"
    "\n**Step 2: Scrape**"
    "\n- Call `scrape_website` on 2-3 of the most relevant URLs for full article content"
    "\n"
    "\n**Step 3: Synthesize**"
    "\n- Combine findings from multiple sources"
    "\n- Track dates, source URLs, and disagreements between sources"
    "\n"
    "\n**Step 4: Complete**"
    "\n- Respond with a summary including source attribution"
    "\n- Note uncertainty or missing evidence where relevant"
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
