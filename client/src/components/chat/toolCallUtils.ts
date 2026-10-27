/**
 * Parse <tool_call> XML blocks from LLM response text.
 *
 * The LLM emits tool calls in this format:
 *   <tool_call>
 *   <function=function_name>
 *   <parameter=param_name>
 *   value
 *   </parameter>
 *   </function>
 *   </tool_call>
 *
 * This module extracts those blocks and returns a cleaned version
 * of the text without the XML markup.
 */

export interface ParsedToolCall {
  functionName: string;
  parameters: Record<string, string>;
  rawXml: string;
}

export interface ToolCallParseResult {
  toolCalls: ParsedToolCall[];
  cleanContent: string;
}

const TOOL_CALL_RE = /<tool_call>(.*?)<\/tool_call>/gs;
const FUNCTION_RE = /<function=(\w+)>/;
const PARAM_RE = /<parameter=(\w+)>([\s\S]*?)<\/parameter>/g;

/**
 * Parse all complete <tool_call> blocks from text.
 */
export function parseToolCallContent(text: string): ToolCallParseResult {
  const toolCalls: ParsedToolCall[] = [];
  let cleanContent = text;

  let match: RegExpExecArray | null;
  while ((match = TOOL_CALL_RE.exec(text)) !== null) {
    const rawXml = match[0];
    const body = match[1];

    // Extract function name
    const funcMatch = body.match(FUNCTION_RE);
    const functionName = funcMatch ? funcMatch[1] : "unknown";

    // Extract parameters
    const parameters: Record<string, string> = {};
    let paramMatch: RegExpExecArray | null;
    const paramRe = new RegExp(PARAM_RE.source, "g");
    while ((paramMatch = paramRe.exec(body)) !== null) {
      const key = paramMatch[1];
      const value = paramMatch[2].trim();
      parameters[key] = value;
    }

    toolCalls.push({ functionName, parameters, rawXml });
  }

  // Remove all tool call blocks from the visible text
  if (toolCalls.length > 0) {
    cleanContent = text.replace(TOOL_CALL_RE, "").trim();
  }

  return { toolCalls, cleanContent };
}

/**
 * Check whether a streaming buffer currently has an incomplete (unclosed)
 * <tool_call> block.
 */
export function hasPartialToolCall(text: string): boolean {
  return /<tool_call>[\s\S]*$/.test(text) && !/<\/tool_call>/.test(text);
}

/**
 * Extract the raw partial tool call body for display during streaming.
 * Strips the opening <tool_call> tag so only the inner content is shown.
 */
export function extractPartialToolCall(text: string): string {
  const idx = text.indexOf("<tool_call>");
  if (idx === -1) return "";
  const after = text.slice(idx + "<tool_call>".length);
  return after.replace(/<\/tool_call>[\s\S]*$/, "").trim();
}
