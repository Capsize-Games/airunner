"""Search-result and document prompt builders for node functions."""

import json
import re
from typing import Any


class SearchResultsPromptMixin:
    """Build synthesis and verification prompts for tool results."""

    _PREMISE_PRIMARY_EXCERPT_PREFIXES = (
        "Current setting.",
        "Inciting incident.",
    )

    _PREMISE_SECONDARY_EXCERPT_PREFIXES = (
        "Nested anecdote.",
        "Frame narrative.",
        "Background detail.",
        "Production context.",
    )

    @staticmethod
    def _build_answer_text_contract() -> str:
        """Return the structured answer-text contract for internal stages."""
        return (
            "Return ONLY one answer_text block. Use this exact structure:\n"
            "<answer_text>\n"
            "completed reply goes here\n"
            "</answer_text>\n"
            "Replace the example body with the actual completed reply. Do "
            "not copy placeholder text, tag names, ellipses, or "
            "instructions inside the tags. Do not include any text before "
            "or after the answer_text block."
        )

    @staticmethod
    def _extract_document_requested_analysis(all_tool_content: str) -> str:
        """Return the requested analysis recorded by document tools."""
        match = re.search(
            r"^Requested analysis:\s*(.+)$",
            str(all_tool_content or ""),
            flags=re.MULTILINE,
        )
        if match is None:
            return ""
        return match.group(1).strip()

    @staticmethod
    def _extract_document_supporting_evidence(
        all_tool_content: str,
    ) -> str:
        """Return the supporting-evidence section from document analysis."""
        content = str(all_tool_content or "")
        marker = "Supporting evidence:\n\n"
        if marker in content:
            return content.split(marker, 1)[1].strip()
        match = re.search(
            r"Supporting evidence:\s*(.*)\Z",
            content,
            flags=re.DOTALL,
        )
        if match is None:
            return ""
        return match.group(1).strip()

    @staticmethod
    def _extract_document_analysis_mode(all_tool_content: str) -> str:
        """Return the analysis mode recorded by document-analysis tools."""
        match = re.search(
            r"^Analysis mode:\s*(.+)$",
            str(all_tool_content or ""),
            flags=re.MULTILINE,
        )
        if match is None:
            return ""
        return match.group(1).strip()

    def _extract_document_structured_analysis(
        self: Any,
        all_tool_content: str,
    ) -> str:
        """Return one structured-document-analysis section when present."""
        return self._extract_document_analysis_section(
            all_tool_content,
            "Structured document analysis",
            (
                "Refined whole-document synthesis",
                "Chunk summaries",
                "Supporting evidence",
            ),
        )

    def _extract_document_structured_analysis_payload(
        self: Any,
        all_tool_content: str,
    ) -> dict[str, Any]:
        """Return parsed structured-document-analysis data when valid."""
        raw_analysis = self._extract_document_structured_analysis(
            all_tool_content,
        )
        if not raw_analysis:
            return {}
        try:
            payload = json.loads(raw_analysis)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _collect_structured_narrative_layers(
        payload: dict[str, Any],
    ) -> set[str]:
        """Return normalized narrative-layer labels from one payload."""
        layers: set[str] = set()
        primary = str(payload.get("primary_narrative_layer") or "").strip()
        if primary:
            layers.add(primary)
        secondary = payload.get("secondary_narrative_layers")
        if not isinstance(secondary, list):
            return layers
        for value in secondary:
            label = str(value or "").strip()
            if label:
                layers.add(label)
        return layers

    def _build_structured_document_guidance(
        self: Any,
        all_tool_content: str,
        *,
        for_verification: bool = False,
    ) -> str:
        """Return prompt guidance derived from structured analysis."""
        payload = self._extract_document_structured_analysis_payload(
            all_tool_content,
        )
        if not payload:
            return ""

        parts = [
            "If structured document analysis is present below, treat it as "
            "grounded evidence about narrative layers and composition "
            "cautions.",
        ]
        layers = self._collect_structured_narrative_layers(payload)
        if layers.intersection(
            {
                "frame_or_recollection",
                "layered_or_mixed",
                "production_process",
            }
        ):
            parts.append(
                "Keep staged, remembered, quoted, and frame-level material "
                "separate from literal story-world events unless the "
                "evidence states that transition explicitly."
            )
            parts.append(
                "Treat production-context or frame-layer excerpts as "
                "describing staging, authorship, recollection, or "
                "constructed scenes unless the evidence explicitly says "
                "those acts occur in the primary story world."
            )
            if for_verification:
                parts.append(
                    "If the draft collapses those layers into direct plot "
                    "events, narrator agency, or confirmed motives, treat "
                    "that as unsupported and rewrite it."
                )
            else:
                parts.append(
                    "Do not collapse those layers into direct plot events, "
                    "narrator agency, or confirmed motives unless the "
                    "evidence states that explicitly."
                )

        cautions = payload.get("composition_cautions")
        if isinstance(cautions, list):
            caution_items = [
                str(item or "").strip()
                for item in cautions
                if str(item or "").strip()
            ]
        else:
            caution_items = []
        if caution_items:
            if for_verification:
                parts.append(
                    "If the draft violates those composition cautions, "
                    "treat that as unsupported and rewrite it."
                )
            else:
                parts.append(
                    "Follow those composition cautions when composing the "
                    "answer."
                )
            parts.append(
                "Grounded composition cautions: "
                f"{'; '.join(caution_items[:3])}."
            )

        return " ".join(parts) + "\n\n"

    def _should_preserve_secondary_premise_context(
        self: Any,
        all_tool_content: str,
    ) -> bool:
        """Return whether premise prompts should keep one secondary excerpt."""
        layers = self._collect_structured_narrative_layers(
            self._extract_document_structured_analysis_payload(
                all_tool_content,
            )
        )
        return bool(
            layers.intersection(
                {
                    "frame_or_recollection",
                    "layered_or_mixed",
                    "production_process",
                }
            )
        )

    @staticmethod
    def _extract_document_analysis_section(
        all_tool_content: str,
        heading: str,
        stop_headings: tuple[str, ...],
    ) -> str:
        """Return one named analyze_loaded_document section."""
        content = str(all_tool_content or "")
        marker = f"{heading}:\n\n"
        if marker not in content:
            return ""

        tail = content.split(marker, 1)[1]
        end = len(tail)
        for stop_heading in stop_headings:
            stop_marker = f"\n\n{stop_heading}:\n\n"
            index = tail.find(stop_marker)
            if index != -1:
                end = min(end, index)
        return tail[:end].strip()

    @staticmethod
    def _replace_current_document_label(
        prompt_results: str,
        document_label: str,
    ) -> str:
        """Return summary evidence with one normalized document label."""
        if not prompt_results or not document_label:
            return prompt_results
        return re.sub(
            r"^Current document:\s*loaded document$",
            f"Current document: {document_label}",
            prompt_results,
            count=1,
            flags=re.MULTILINE,
        )

    def _resolve_document_prompt_context(
        self: Any,
        tool_name: str,
        all_tool_content: str,
        user_question: str,
    ) -> tuple[str | None, str | None]:
        """Return intent and summary focus for one document answer prompt."""
        return (
            self._get_document_query_intent(user_question),
            self._get_document_summary_focus(user_question),
        )

    def _build_search_results_prompt(
        self: Any,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        *,
        structured_answer: bool = False,
    ) -> str:
        """Build one no-tool synthesis prompt for search results."""
        question_context = (
            f"User's question: {user_question}\n\n"
            if user_question
            else ""
        )
        rag_guidance = ""
        response_style = "Avoid repetition and be concise."
        prompt_results = all_tool_content
        prompt_results_label = "Search results"
        document_tool = self._is_document_result_tool(tool_name)
        document_intent, document_summary_focus = (
            self._resolve_document_prompt_context(
                tool_name,
                all_tool_content,
                user_question,
            )
        )
        if document_tool:
            if document_intent == "identity":
                rag_guidance = (
                    "If the user is asking what the document is, answer "
                    "directly and briefly by naming the document and, "
                    "when available, its title, author, or file type. "
                    "Do not mention search results or instructions.\n\n"
                )
            elif document_intent == "structure":
                rag_guidance = (
                    "If the user is asking for chapters, sections, or the "
                    "document structure, answer with the section names only. "
                    "Do not restate the document title, author, file type, "
                    "stored path, or any broader summary unless the user "
                    "explicitly asks for them.\n\n"
                )
            elif document_intent == "summary":
                prompt_results = self._build_document_summary_prompt_results(
                    all_tool_content,
                    summary_focus=document_summary_focus,
                )
                if prompt_results != all_tool_content:
                    prompt_results_label = (
                        "Document analysis context"
                        if "Analysis mode:" in all_tool_content
                        else "Evidence excerpts"
                    )
                has_evidence_role_labels = any(
                    label in prompt_results
                    for label in (
                        "Current setting.",
                        "Inciting incident.",
                    )
                )
                structured_guidance = (
                    self._build_structured_document_guidance(
                        all_tool_content,
                    )
                )
                summary_guidance = (
                    "If the user is asking for a summary of the document, "
                    "synthesize the evidence below into a substantive "
                    "overview. Explain the central worldview, argument, or "
                    "subject first, then cover the most important supporting "
                    "ideas, claims, practices, or concrete details that "
                    "appear in the excerpts. Merge overlapping evidence into "
                    "one coherent answer instead of repeating it. Prefer "
                    "specific details over vague labels. Keep isolated "
                    "front-matter anecdotes or biographical trivia secondary "
                    "unless the same idea recurs elsewhere in the evidence. "
                    "Stay anchored to what the excerpts explicitly say. Do "
                    "not infer genre, series, trilogy, collection, or "
                    "bibliographic relationships unless the evidence states "
                    "them directly. Do not turn ambiguous mood, imagery, or "
                    "one-off wording into confirmed plot facts, motives, or "
                    "beliefs unless the excerpts state that directly. The evidence "
                    "below already comes from the currently loaded document "
                    "the user is asking about. Do not ask the user to "
                    "identify which book, story, document, title, or author "
                    "they mean when that evidence is already present. Write "
                    "7 to 10 sentences in 2 to 4 short paragraphs. Do not "
                    "repeat the document title, author, or structure unless "
                    "the user asked for them. Do not answer with bare "
                    "category labels such as 'Setting, Premise, Conflict, "
                    "Characters.' Write full sentences only. Do not mention "
                    "file names, stored paths, excerpt numbers, search "
                    "results, or internal instructions. Do not use bullet "
                    "points, numbered lists, or excerpt inventories.\n\n"
                )
                if document_summary_focus == "premise":
                    role_guidance = (
                        "If the evidence includes explicit setup or "
                        "catalyst spans, lead with those first and keep "
                        "secondary context subordinate unless it is "
                        "reinforced by more than one excerpt.\n\n"
                        if has_evidence_role_labels
                        else ""
                    )
                    rag_guidance = (
                        "If the user is asking what the book, story, or "
                        "document is about, lead with the premise, setting, "
                        "central conflict, and the most important character "
                        "relationships first. Treat isolated later scenes, "
                        "one-off travel stops, and stray dialogue fragments "
                        "as secondary unless the evidence clearly shows they "
                        "define the work as a whole. Prefer the inciting "
                        "development and main causal setup over static "
                        "character descriptions or travel anecdotes. "
                        "Treat later arguments, recollections, quoted "
                        "remarks, and atmospheric fragments as secondary to "
                        "the inciting mystery unless multiple excerpts make "
                        "them central. Do not introduce generic dramatic "
                        "padding, extra motives, or relationship dynamics "
                        "unless the excerpts explicitly support them.\n\n"
                        + structured_guidance
                        + role_guidance
                        + summary_guidance
                    )
                    response_style = (
                        "Lead with premise, setting, and central conflict. "
                        "Keep stray scene details secondary and favor the "
                        "clearest grounded reading supported by the "
                        "excerpts. Prioritize the main setup over static "
                        "character profiles."
                    )
                else:
                    rag_guidance = structured_guidance + summary_guidance
                    response_style = (
                        "Start with the central themes, not opening trivia. "
                        "Synthesize across excerpts and avoid repetition."
                    )
            elif document_intent == "compare":
                rag_guidance = (
                    "If the user is asking for a comparison, compare only "
                    "the people, sections, claims, or results that the "
                    "document evidence actually supports. Separate the most "
                    "important similarities from the most important "
                    "differences when helpful. If the evidence only covers "
                    "one side of the requested comparison, say so briefly "
                    "instead of filling gaps.\n\n"
                )
                response_style = (
                    "Keep the comparison structured, direct, and grounded in "
                    "the excerpts."
                )
            elif document_intent == "extract":
                rag_guidance = (
                    "If the user is asking you to extract or pull out "
                    "specific information, return only the supported names, "
                    "dates, values, measurements, labels, or facts that the "
                    "document states. Preserve exact wording for concrete "
                    "values when possible. If a requested field is missing, "
                    "say it is not stated instead of guessing.\n\n"
                )
                response_style = (
                    "Use labeled lines or a short list when that makes the "
                    "extracted information easier to read."
                )
            elif document_intent == "list":
                rag_guidance = (
                    "If the user is asking for a list or enumeration, "
                    "extract only the items the document supports. "
                    "Deduplicate overlapping items, keep them concise, and "
                    "preserve exact wording for names, dates, headings, or "
                    "values when useful.\n\n"
                )
                response_style = (
                    "Prefer a compact, readable list if that best matches the "
                    "user's request."
                )
            elif document_intent == "transform":
                rag_guidance = (
                    "If the user is asking you to organize or reformat "
                    "document information, follow the requested structure as "
                    "closely as the evidence allows. Keep the answer factual, "
                    "clear, and readable. If the requested layout is more "
                    "specific than the evidence supports, provide the closest "
                    "clear structure without inventing missing data.\n\n"
                )
                response_style = (
                    "Follow the requested structure while keeping every field "
                    "grounded in the excerpts."
                )
            else:
                rag_guidance = (
                    "Use document identity fields only when they help answer "
                    "the user's question. Do not repeat the document title, "
                    "author, file type, stored path, or document structure "
                    "unless they are needed for the answer.\n\n"
                )

        prompt_intro = (
            "You are answering a question about a currently loaded document "
            "using document evidence. Respond naturally and conversationally.\n\n"
            if document_tool
            else "You are answering a question based on search results. "
            "Respond naturally and conversationally.\n\n"
        )
        if document_tool and structured_answer:
            response_instruction = (
                "Based on the document evidence above, provide a clear, "
                "conversational answer to the user's question about that "
                "document. Use ONLY the information from the document evidence. "
                "The excerpts already belong to the loaded document the user is "
                "asking about, so do not ask which book, story, or document they "
                "mean unless no document evidence is present. Do not call any "
                "tools and do not use JSON. "
                f"{self._build_answer_text_contract()}"
            )
        else:
            response_instruction = (
                "Based on the document evidence above, provide a clear, "
                "conversational answer to the user's question about that "
                "document. Use ONLY the information from the document evidence. "
                "The excerpts already belong to the loaded document the user is "
                "asking about, so do not ask which book, story, or document they "
                "mean unless no document evidence is present. Do not call any "
                "tools, do not use JSON, and do not prefix the reply with labels "
                "like Draft:, Answer:, or Response:. Just write a natural "
                "response."
                if document_tool
                else "Based on the search results above, provide a clear, "
                "conversational answer to the user's question. Use ONLY the "
                "information from the search results. Do not call any tools, do "
                "not use JSON, and do not prefix the reply with labels like "
                "Draft:, Answer:, or Response:. Just write a natural response."
            )

        return (
            f"{prompt_intro}"
            f"{question_context}"
            f"{rag_guidance}"
            f"{prompt_results_label}:\n"
            f"{prompt_results}\n\n"
            f"{response_instruction} {response_style}"
        )

    def _build_search_results_verification_prompt(
        self: Any,
        all_tool_content: str,
        tool_name: str,
        user_question: str,
        drafted_response: str,
        *,
        structured_answer: bool = False,
    ) -> str:
        """Build a verification prompt for the final document answer."""
        prompt_results = all_tool_content
        prompt_results_label = "Search results"
        document_intent, document_summary_focus = (
            self._resolve_document_prompt_context(
                tool_name,
                all_tool_content,
                user_question,
            )
        )
        has_evidence_role_labels = any(
            label in prompt_results
            for label in (
                "Current setting.",
                "Inciting incident.",
                "Nested anecdote.",
                "Frame narrative.",
                "Background detail.",
            )
        )
        structured_document_analysis = self._extract_document_structured_analysis(
            all_tool_content,
        )
        if (
            self._is_document_result_tool(tool_name)
            and document_intent == "summary"
        ):
            prompt_results = self._build_document_summary_prompt_results(
                all_tool_content,
                summary_focus=document_summary_focus,
            )
            if prompt_results != all_tool_content:
                prompt_results_label = (
                    "Document analysis context"
                    if "Analysis mode:" in all_tool_content
                    else "Evidence excerpts"
                )

        draft_block = drafted_response.strip()
        if draft_block:
            draft_instruction = (
                "Draft answer to verify:\n"
                f"{draft_block}\n\n"
            )
        else:
            draft_instruction = (
                "Draft answer to verify:\n"
                "The initial draft was empty or unusable. Rebuild the final "
                "answer directly from the evidence below.\n\n"
            )

        response_style = (
            "Write 7 to 10 sentences in 2 to 4 short paragraphs."
            if document_intent == "summary"
            else "Return the extracted information in a clear structure."
            if document_intent == "extract"
            else "Return a clear, readable list when the user asked for one."
            if document_intent == "list"
            else "Return the requested structure as clearly as the evidence allows."
            if document_intent == "transform"
            else "Answer directly in one or two concise paragraphs."
        )
        if document_intent == "summary":
            structured_guidance = self._build_structured_document_guidance(
                all_tool_content,
                for_verification=True,
            )
            if document_summary_focus == "premise":
                verification_focus = (
                    "Lead with the premise, setting, central conflict, and "
                    "major relationships that the excerpts support. Prefer "
                    "recurring core details over isolated late-scene "
                    "events. Remove generic dramatic padding unless the "
                    "excerpts explicitly support it. "
                    + structured_guidance
                )
                if has_evidence_role_labels:
                    verification_focus += (
                        " If the evidence includes explicit setup or "
                        "catalyst spans, keep those in the lead and push "
                        "secondary context into the background."
                    )
            else:
                verification_focus = (
                    "Lead with the document's central subject, major themes, "
                    "or recurring claims that the excerpts support. Prefer "
                    "the strongest repeated evidence over isolated details. "
                    + structured_guidance
                )
        elif document_intent == "extract":
            verification_focus = (
                "Keep exact supported values and remove guessed or merged "
                "fields."
            )
        elif document_intent == "list":
            verification_focus = (
                "Keep only supported items, remove duplicates, and do not pad "
                "the list with inferences."
            )
        elif document_intent == "compare":
            verification_focus = (
                "Compare only supported similarities and differences, and "
                "remove unsupported contrasts."
            )
        elif document_intent == "transform":
            verification_focus = (
                "Follow the requested structure, but drop fields the evidence "
                "does not support."
            )
        else:
            verification_focus = (
                "Prefer the clearest directly supported claims and remove "
                "anything the evidence does not clearly support."
            )
        clarification_guidance = (
            "The evidence below already belongs to the currently loaded "
            "document the user is asking about. Do not respond with a "
            "clarification request about which book, story, or document they "
            "mean, and do not ask for the title or author, when that "
            "document evidence is already present.\n"
            if self._is_document_result_tool(tool_name)
            else ""
        )

        answer_contract = (
            self._build_answer_text_contract()
            if structured_answer
            else "Return only the final user-facing answer."
        )

        return (
            "You are verifying and finalizing a document-grounded answer.\n\n"
            f"User question: {user_question}\n\n"
            f"{draft_instruction}"
            f"{prompt_results_label}:\n{prompt_results}\n\n"
            f"{clarification_guidance}"
            "Check the draft against the evidence and keep only supported "
            "claims. Rewrite or remove unsupported details, instruction "
            "leakage, or unsupported scene details. If the draft is weak, ignore "
            "it and answer directly from the evidence. If the evidence is "
            "incomplete, say so briefly instead of guessing.\n"
            "Do not treat a draft claim as supported just because matching "
            "words appear in the evidence. Verify the structural status of "
            "each claim: whether it belongs to the document's primary frame, "
            "to a nested quote, anecdote, example, citation, hypothetical, "
            "or to a staged or constructed artifact. If the draft promotes "
            "nested or constructed material into primary document reality, "
            "rewrite or remove that claim.\n"
            "Do not answer with claim-by-claim verdicts such as Supported, "
            "Not supported, or Partially supported.\n"
            "Do not answer with bare category labels such as 'Setting, "
            "Premise, Conflict, Characters.' Write complete sentences only.\n"
            f"{verification_focus}\n"
            f"{response_style}\n"
            "Do not mention search results, verification, instructions, file "
            "names, stored paths, excerpt numbers, labels like Draft:, "
            "Verified:, Answer:, or Response:, or any internal reasoning "
            f"steps. {answer_contract}"
        )

    @staticmethod
    def _extract_rag_excerpt_bodies(all_tool_content: str) -> list[str]:
        """Return cleaned excerpt bodies from one formatted RAG result."""
        excerpt_pattern = re.compile(
            r"\[Excerpt \d+(?: from [^\]]+)?\]\n"
            r"(.*?)(?=\n\n\[Excerpt \d+(?: from [^\]]+)?\]\n|\Z)",
            flags=re.DOTALL,
        )
        excerpts: list[str] = []
        for match in excerpt_pattern.finditer(str(all_tool_content or "")):
            excerpt = " ".join(match.group(1).split())
            if excerpt and excerpt not in excerpts:
                excerpts.append(excerpt)
        return excerpts

    def _select_premise_summary_excerpts(
        self,
        excerpts: list[str],
        *,
        preserve_secondary_context: bool = False,
    ) -> list[str]:
        """Return the highest-signal excerpt subset for premise summaries."""
        if not excerpts:
            return []

        primary_excerpts = [
            excerpt
            for excerpt in excerpts
            if excerpt.startswith(self._PREMISE_PRIMARY_EXCERPT_PREFIXES)
        ]
        secondary_excerpts = [
            excerpt
            for excerpt in excerpts
            if excerpt.startswith(self._PREMISE_SECONDARY_EXCERPT_PREFIXES)
        ]
        supporting_excerpts = [
            excerpt
            for excerpt in excerpts
            if not excerpt.startswith(self._PREMISE_SECONDARY_EXCERPT_PREFIXES)
            and excerpt not in primary_excerpts
        ]

        selected: list[str] = []
        if preserve_secondary_context and secondary_excerpts:
            if primary_excerpts:
                selected.append(primary_excerpts[0])
            for excerpt in secondary_excerpts:
                if excerpt in selected:
                    continue
                selected.append(excerpt)
                break
        else:
            selected = primary_excerpts[:3]

        remaining_primary_excerpts = [
            excerpt for excerpt in primary_excerpts if excerpt not in selected
        ]
        for excerpt in remaining_primary_excerpts:
            if excerpt in selected:
                continue
            selected.append(excerpt)
            if len(selected) >= 3:
                break
        for excerpt in supporting_excerpts:
            if excerpt in selected:
                continue
            selected.append(excerpt)
            if len(selected) >= 3:
                break

        return selected or excerpts[:3]

    @staticmethod
    def _extract_primary_document_label(all_tool_content: str) -> str:
        """Return the first matched-document label when available."""
        for line in str(all_tool_content or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("Current document: "):
                return stripped.removeprefix("Current document: ").strip()
            if stripped.startswith("Document: "):
                return stripped.removeprefix("Document: ").strip()
            if stripped.startswith("Document 1: "):
                return stripped.removeprefix("Document 1: ").strip()
        return ""

    def _build_document_summary_prompt_results(
        self,
        all_tool_content: str,
        *,
        summary_focus: str | None = None,
    ) -> str:
        """Return excerpt-focused synthesis input for document summaries."""
        analysis_mode = self._extract_document_analysis_mode(all_tool_content)
        preserve_secondary_context = (
            summary_focus == "premise"
            and self._should_preserve_secondary_premise_context(
                all_tool_content,
            )
        )
        excerpts = self._extract_rag_excerpt_bodies(all_tool_content)
        if summary_focus == "premise":
            excerpts = self._select_premise_summary_excerpts(
                excerpts,
                preserve_secondary_context=preserve_secondary_context,
            )
        document_label = self._extract_primary_document_label(all_tool_content)
        structured_document_analysis = self._extract_document_structured_analysis(
            all_tool_content,
        )
        sections: list[str] = []
        if analysis_mode == "full_document":
            full_document_text = self._extract_document_analysis_section(
                all_tool_content,
                "Full document text",
                (),
            )
            if document_label:
                sections.append(f"Current document: {document_label}")
            if structured_document_analysis:
                sections.append(
                    "Structured document analysis:\n"
                    f"{structured_document_analysis}"
                )
            if full_document_text:
                sections.append(f"Full document text:\n{full_document_text}")
            if sections:
                return "\n\n".join(sections)
        if analysis_mode == "chunked_document":
            coverage_outline = self._extract_document_analysis_section(
                all_tool_content,
                "Document coverage",
                (
                    "Refined whole-document synthesis",
                    "Chunk summaries",
                    "Supporting evidence",
                ),
            )
            supporting_evidence = self._extract_document_supporting_evidence(
                all_tool_content,
            )
            refined_synthesis = self._extract_document_analysis_section(
                all_tool_content,
                "Refined whole-document synthesis",
                ("Chunk summaries", "Supporting evidence"),
            )
            chunk_summaries = self._extract_document_analysis_section(
                all_tool_content,
                "Chunk summaries",
                ("Supporting evidence",),
            )
            if document_label:
                sections.append(f"Current document: {document_label}")
            if coverage_outline:
                sections.append(
                    f"Document coverage:\n{coverage_outline}"
                )
            if structured_document_analysis:
                sections.append(
                    "Structured document analysis:\n"
                    f"{structured_document_analysis}"
                )
            evidence_excerpts: list[str] = []
            if supporting_evidence:
                evidence_results = self._replace_current_document_label(
                    supporting_evidence,
                    document_label,
                )
                evidence_excerpts = self._extract_rag_excerpt_bodies(
                    evidence_results,
                )
                if summary_focus == "premise":
                    evidence_excerpts = self._select_premise_summary_excerpts(
                        evidence_excerpts,
                        preserve_secondary_context=(
                            preserve_secondary_context
                        ),
                    )
            if refined_synthesis:
                sections.append(
                    "Refined whole-document synthesis:\n"
                    f"{refined_synthesis}"
                )
                if summary_focus == "premise" and evidence_excerpts:
                    sections.extend(
                        evidence_excerpts[
                            : 3 if preserve_secondary_context else 2
                        ]
                    )
                return "\n\n".join(sections)
            if evidence_excerpts:
                sections.extend(evidence_excerpts)
                return "\n\n".join(sections)
            if chunk_summaries:
                sections.append(f"Chunk summaries:\n{chunk_summaries}")
            if len(sections) > 1:
                return "\n\n".join(sections)
        if document_label:
            sections.append(f"Current document: {document_label}")
        if not excerpts:
            supporting_evidence = self._extract_document_supporting_evidence(
                all_tool_content
            )
            if supporting_evidence:
                supporting_evidence = self._replace_current_document_label(
                    supporting_evidence,
                    document_label,
                )
                if "Current document:" in supporting_evidence:
                    sections.clear()
                sections.append(supporting_evidence)
                return "\n\n".join(sections)
            if sections:
                sections.append(all_tool_content)
                return "\n\n".join(sections)
            return all_tool_content
        sections.extend(excerpts)
        return "\n\n".join(sections)