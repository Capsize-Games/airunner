// conversation.js: Minimal chat widget logic with MathJax integration

let chatBridge = null;
window.isChatReady = false;
window.chatReady = new Promise((resolve) => {
    window.chatReadyResolve = resolve;
});
window.autoScrollEnabled = true;

function getStreamTargetMessage(container, requestId) {
    if (!container) return null;

    if (requestId) {
        const escapedRequestId =
            typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
                ? CSS.escape(requestId)
                : requestId.replace(/"/g, '\\"');
        const requestMessage = container.querySelector(
            `.message.assistant[data-request-id="${escapedRequestId}"]`
        );
        if (requestMessage) {
            return requestMessage;
        }
    }

    const messages = container.querySelectorAll(
        '.message.assistant:not(.tool-status):not(.thinking-block)'
    );
    return messages.length ? messages[messages.length - 1] : null;
}

function enableAutoScroll() { window.autoScrollEnabled = true; }
function disableAutoScroll() { window.autoScrollEnabled = false; }
function isScrolledToBottom(container, tolerance = 8) {
    return Math.abs(container.scrollHeight - container.scrollTop - container.clientHeight) <= tolerance;
}
function attachScrollListener(container) {
    if (!container._scrollListenerAttached) {
        container.addEventListener('scroll', () => {
            isScrolledToBottom(container) ? enableAutoScroll() : disableAutoScroll();
        });
        container._scrollListenerAttached = true;
    }
}

function fallbackCopyText(text) {
    try {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        return true;
    } catch {
        return false;
    }
}

function copyTextToClipboard(text) {
    const normalized = String(text || '');
    if (!normalized.trim()) {
        return Promise.resolve(false);
    }

    if (
        typeof navigator !== 'undefined'
        && navigator.clipboard
        && typeof navigator.clipboard.writeText === 'function'
    ) {
        return navigator.clipboard.writeText(normalized)
            .then(() => true)
            .catch(() => fallbackCopyText(normalized));
    }

    return Promise.resolve(fallbackCopyText(normalized));
}

function initializeChatView() {
    const container = document.getElementById('conversation-container');
    if (!container) return;
    attachScrollListener(container);
    new QWebChannel(qt.webChannelTransport, function (channel) {
        chatBridge = channel.objects.chatBridge;
        window.chatBridge = chatBridge;
        console.log('[conversation.js] QWebChannel initialized. chatBridge:', chatBridge);
        if (!chatBridge) {
            console.error('[conversation.js] chatBridge not found on QWebChannel.');
            return;
        }
        chatBridge.appendMessage.connect(appendMessage);
        chatBridge.clearMessages.connect(clearMessages);
        chatBridge.toolStatusUpdate.connect(handleToolStatusUpdate);
        chatBridge.modelLoadStatusUpdate.connect(handleModelLoadStatusUpdate);
        chatBridge.setMessages.connect(function (msgs) {
            // Clear everything when setting messages (loading from saved data)
            // Tool status and thinking widgets will be recreated from saved message data
            clearMessages();

            enableAutoScroll();
            const renderPromises = msgs.map(m => appendMessage(m, false));
            Promise.all(renderPromises).then(() => {
                if (window.autoScrollEnabled) {
                    setTimeout(smoothScrollToBottom, 0);
                    setTimeout(smoothScrollToBottom, 100);
                    setTimeout(smoothScrollToBottom, 300);
                }
            });
        });
        chatBridge.updateLastMessageContent.connect(function (
            requestId,
            content,
            contentType,
        ) {
            // Update the message for the active request during streaming.
            const container = document.getElementById('conversation-container');
            if (!container) return;

            const targetMessage = getStreamTargetMessage(container, requestId);
            if (!targetMessage) return;

            const contentDiv = targetMessage.querySelector('.content');
            if (!contentDiv) return;

            const previousContentType = targetMessage.getAttribute(
                'data-content-type'
            ) || '';
            const nextContentType = contentType || previousContentType;
            targetMessage.setAttribute('data-content-type', nextContentType);

            // Update content with sanitized HTML
            contentDiv.innerHTML = sanitizeContent(content, nextContentType);

            // Trigger MathJax typesetting if needed
            if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
                window.MathJax.typesetPromise([contentDiv]);
            }

            // Auto-scroll if enabled
            if (window.autoScrollEnabled) {
                smoothScrollToBottom();
            }
        });
        chatBridge.thinkingStatusUpdate.connect(handleThinkingStatusUpdate);
        window.isChatReady = true;
        if (window.chatReadyResolve) {
            window.chatReadyResolve();
            delete window.chatReadyResolve;
        }
        setTimeout(smoothScrollToBottom, 50);
    });
    const observer = new MutationObserver((mutations) => {
        let needsScroll = false, needsTypeset = false;
        for (const mutation of mutations) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                needsScroll = true;
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) needsTypeset = true;
                });
            } else if (mutation.type === 'characterData') {
                needsTypeset = true;
            }
        }
        if (needsScroll) {
            // Only auto-scroll when the user hasn't manually scrolled up
            if (window.autoScrollEnabled) {
                setTimeout(smoothScrollToBottom, 0);
            }
        }
        if (needsTypeset && window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
            clearTimeout(window.mathJaxTypesetTimeout);
            window.mathJaxTypesetTimeout = setTimeout(() => {
                window.MathJax.typesetPromise([container]);
            }, 50);
        }
    });
    observer.observe(container, { childList: true, subtree: true, characterData: true });
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function looksLikeHtmlContent(content) {
    if (typeof content !== 'string') return false;
    return /<\/?[a-z][\w:-]*(?:\s[^<>]*)?>/i.test(content);
}

function formatPlainTextParagraphs(content) {
    if (typeof content !== 'string' || !content) return '';

    const paragraphs = content
        .split(/\n{2,}/)
        .map((paragraph) => paragraph.trim())
        .filter(Boolean);

    if (!paragraphs.length) {
        return '';
    }

    return paragraphs
        .map((paragraph) => {
            const escaped = escapeHtml(paragraph).replace(/\n/g, '<br>');
            return `<p>${escaped}</p>`;
        })
        .join('');
}

function normalizeContentForRender(html, contentType = '') {
    let content = html;

    if (typeof content !== 'string') return '';
    content = content.trim();

    // If content looks like a JSON string (wrapped in quotes with escaped chars), unescape it
    if (content.startsWith('"') && content.endsWith('"')) {
        try {
            content = JSON.parse(content);
        } catch (e) {
            // Manual unescape if JSON.parse fails
            content = content.slice(1, -1)
                .replace(/\\n/g, '\n')
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, '\\');
        }
    }

    // Remove leading/trailing empty paragraphs, divs, and excessive whitespace
    content = content
        .replace(/^(\s*<(p|div|br)[^>]*>\s*<\/(p|div)>\s*)+/gi, '')
        .replace(/(\s*<(p|div|br)[^>]*>\s*<\/(p|div)>\s*)+$/gi, '')
        .replace(/^(<br\s*\/?>)+/gi, '')
        .replace(/(<br\s*\/?>)+$/gi, '')
        .replace(/^\s+/, '')
        .replace(/\s+$/, '');

    const normalizedType = String(contentType || '').toLowerCase();
    if (!content) {
        return '';
    }

    if (normalizedType === 'plaintext' || !looksLikeHtmlContent(content)) {
        return formatPlainTextParagraphs(content);
    }

    return content;
}

function sanitizeContent(html, contentType = '') {
    // Content may include HTML from the backend; treat it as untrusted and sanitize.
    const content = normalizeContentForRender(html, contentType);
    return sanitizeHtmlAllowlist(content);
}

function isSafeLinkHref(href) {
    if (!href) return false;
    const v = String(href).trim().toLowerCase();
    return v.startsWith('http://') || v.startsWith('https://') || v.startsWith('mailto:') || v.startsWith('#');
}

function sanitizeHtmlAllowlist(html) {
    // Allow a minimal set of tags needed for chat formatting.
    const allowedTags = new Set([
        'A', 'B', 'BR', 'BLOCKQUOTE', 'CODE', 'DIV', 'EM', 'I',
        'LI', 'OL', 'P', 'PRE', 'SPAN', 'STRONG', 'UL',
        'H1', 'H2', 'H3', 'H4', 'H5', 'H6'
    ]);

    const allowedAttrsByTag = {
        'A': new Set(['href', 'title', 'target', 'rel']),
        'CODE': new Set(['class']),
        'PRE': new Set(['class']),
        'SPAN': new Set(['class']),
        'DIV': new Set(['class']),
        'P': new Set(['class']),
    };

    const template = document.createElement('template');
    template.innerHTML = html;

    const walk = (node) => {
        const children = Array.from(node.childNodes);
        for (const child of children) {
            if (child.nodeType === Node.ELEMENT_NODE) {
                const tag = child.tagName.toUpperCase();

                if (!allowedTags.has(tag)) {
                    child.replaceWith(document.createTextNode(child.textContent || ''));
                    continue;
                }

                const allowedAttrs = allowedAttrsByTag[tag] || new Set();
                for (const attr of Array.from(child.attributes)) {
                    const name = attr.name.toLowerCase();

                    if (name.startsWith('on') || name === 'style' || name === 'src' || name === 'srcset') {
                        child.removeAttribute(attr.name);
                        continue;
                    }

                    if (!allowedAttrs.has(name)) {
                        child.removeAttribute(attr.name);
                        continue;
                    }

                    if (tag === 'A' && name === 'href') {
                        if (!isSafeLinkHref(attr.value)) {
                            child.removeAttribute('href');
                        }
                    }

                    if (tag === 'A' && name === 'target') {
                        if (attr.value !== '_blank' && attr.value !== '_self') {
                            child.setAttribute('target', '_blank');
                        }
                    }
                }

                if (tag === 'A') {
                    const target = child.getAttribute('target');
                    if (target === '_blank') {
                        child.setAttribute('rel', 'noopener noreferrer');
                    }
                }

                walk(child);
            } else if (child.nodeType === Node.COMMENT_NODE) {
                child.remove();
            } else if (child.nodeType === Node.TEXT_NODE) {
                // ok
            } else {
                // Drop other node types (processing instructions, etc.)
                child.remove();
            }
        }
    };

    walk(template.content);
    return template.innerHTML;
}

function createMessageElement(msg) {
    // Debug: log the raw content to see what we're receiving
    if (msg.content && (msg.content.includes('<style') || msg.content.includes('pre {'))) {
        console.log('[DEBUG] Message with HTML/CSS detected:', {
            id: msg.id,
            is_bot: msg.is_bot,
            contentPreview: msg.content.substring(0, 500)
        });
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + (msg.is_bot ? 'assistant' : 'user');
    messageDiv.setAttribute('data-message-id', msg.id || Date.now());
    if (msg.request_id) {
        messageDiv.setAttribute('data-request-id', msg.request_id);
    }
    messageDiv.setAttribute('data-content-type', msg.content_type || '');
    const senderDiv = document.createElement('div');
    senderDiv.className = 'sender';
    senderDiv.textContent = msg.name || msg.sender || (msg.is_bot ? 'Assistant' : 'User');

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.innerHTML = sanitizeContent(msg.content, msg.content_type);

    // Header always present so we can attach action buttons for all messages
    let headerDiv = document.createElement('div');
    headerDiv.className = 'header';
    headerDiv.appendChild(senderDiv);

    // Actions container (icon buttons)
    let actionsDiv = document.createElement('div');
    actionsDiv.className = 'actions';

    // Copy button (icon-only)
    const copyButton = document.createElement('button');
    copyButton.className = 'copy-button';
    copyButton.title = 'Copy';
    copyButton.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
    copyButton.onclick = function (e) {
        e.preventDefault();
        try {
            if (window.chatBridge && typeof window.chatBridge.copyMessage === 'function') {
                window.chatBridge.copyMessage(msg.id);
            } else {
                // fallback to in-page copy if bridge not available
                try {
                    const text = (contentDiv && (contentDiv.innerText || contentDiv.textContent)) || (msg.content || '');
                    copyTextToClipboard(text).catch(() => { });
                } catch (err) {
                    if (console && console.warn) console.warn('[conversation.js] fallback copy failed', err);
                }
            }
        } catch (err) {
            if (console && console.warn) console.warn('[conversation.js] copy click handler failed', err);
        }
    };
    actionsDiv.appendChild(copyButton);

    // Delete button (icon-only) - retain existing behavior
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-button';
    deleteButton.title = 'Delete';
    deleteButton.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>`;
    deleteButton.onclick = function (e) {
        e.preventDefault();
        if (window.chatBridge && typeof window.chatBridge.deleteMessage === 'function') {
            window.chatBridge.deleteMessage(msg.id);
        }
    };
    actionsDiv.appendChild(deleteButton);

    headerDiv.appendChild(actionsDiv);

    // Append header and content to message
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    if (msg.timestamp) {
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        try {
            const date = new Date(msg.timestamp);
            timestampDiv.textContent = date.toLocaleString();
        } catch (e) {
            timestampDiv.textContent = msg.timestamp;
        }
        messageDiv.appendChild(timestampDiv);
    }
    return messageDiv;
}

async function appendMessage(msg, scroll = true) {
    const container = document.getElementById('conversation-container');
    if (!container) return;

    // Debug logging
    console.log(`[appendMessage] id=${msg.id}, is_bot=${msg.is_bot}, ` +
        `pre_tool_thinking=${!!msg.pre_tool_thinking}, ` +
        `tool_usage=${msg.tool_usage ? msg.tool_usage.length : 0}, ` +
        `thinking_content=${!!msg.thinking_content}`);

    if (msg.is_bot) {
        const savedStatusWidget = createSavedStatusWidget(msg);
        if (savedStatusWidget) {
            container.appendChild(savedStatusWidget);
        }
    }

    const messageElement = createMessageElement(msg);
    container.appendChild(messageElement);
    if (msg.is_bot && msg.request_id) {
        const widget = document.getElementById(
            getStatusWidgetDomId(msg.request_id)
        );
        if (widget && widget.parentElement === container) {
            container.insertBefore(widget, messageElement);
        }
    }
    if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
        try { await window.MathJax.typesetPromise([messageElement]); } catch { }
    }
    if (scroll && window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
}

const STATUS_WIDGET_MAX_VISIBLE = 2;

function createSavedStatusWidget(msg) {
    const items = [];

    if (msg.pre_tool_thinking) {
        items.push({
            id: `saved-thinking-pre-${msg.id}`,
            type: 'thinking',
            text: 'Completed',
            status: 'completed',
            content: msg.pre_tool_thinking,
        });
    }

    if (msg.tool_usage && Array.isArray(msg.tool_usage)) {
        for (const tool of msg.tool_usage) {
            const displayName = getToolDisplayName(tool.tool_name);
            const queryPreview = tool.query && tool.query.length > 50
                ? `${tool.query.substring(0, 50)}...`
                : (tool.query || '');
            const details = tool.details ? ` - ${tool.details}` : '';
            items.push({
                id: `saved-tool-${tool.tool_id || `${msg.id}-${tool.tool_name}`}`,
                type: 'tool',
                text: `${displayName}${queryPreview ? ` for "${queryPreview}"` : ''}${details}`,
                status: 'completed',
                metadata: tool.metadata || null,
            });
        }
    }

    if (msg.thinking_content) {
        items.push({
            id: `saved-thinking-${msg.id}`,
            type: 'thinking',
            text: 'Completed',
            status: 'completed',
            content: msg.thinking_content,
            metadata: msg.thinking_metadata || null,
        });
    }

    if (!items.length) {
        return null;
    }

    const widget = document.createElement('div');
    widget.className = 'unified-status-widget restored-status-widget';
    if (items.some(item => item.type === 'thinking')) {
        widget.classList.add('has-thinking');
    }

    const header = document.createElement('div');
    header.className = 'unified-status-header';
    header.addEventListener('click', () => {
        widget.classList.toggle('expanded');
    });

    const icon = document.createElement('span');
    icon.className = 'unified-status-icon';
    icon.textContent = '✅';

    const title = document.createElement('span');
    title.className = 'unified-status-title';
    title.textContent = 'Completed';

    const count = document.createElement('span');
    count.className = 'unified-status-count';
    count.textContent = items.length > STATUS_WIDGET_MAX_VISIBLE
        ? `${items.length} items`
        : '';

    const expand = document.createElement('span');
    expand.className = 'unified-status-expand';
    expand.textContent = '▶';

    header.appendChild(icon);
    header.appendChild(title);
    header.appendChild(count);
    header.appendChild(expand);

    const visible = document.createElement('div');
    visible.className = 'unified-status-visible';
    for (const item of items.slice(0, STATUS_WIDGET_MAX_VISIBLE)) {
        visible.appendChild(createStatusItemElement(item));
    }

    const history = document.createElement('div');
    history.className = 'unified-status-history';
    for (const item of items.slice(STATUS_WIDGET_MAX_VISIBLE)) {
        history.appendChild(createStatusItemElement(item));
    }

    widget.addEventListener('click', (event) => {
        const copyButton = event.target.closest('.status-item-copy-toggle');
        if (!copyButton) {
            return;
        }
        event.stopPropagation();
        copyStatusText(buildSavedStatusWidgetCopyText(items));
    });

    widget.appendChild(header);
    const thinkingItem = items.find((item) => item.type === 'thinking' && item.content);
    if (thinkingItem) {
        setThinkingPreviewLine(widget, thinkingItem.content);
    }
    widget.appendChild(visible);
    widget.appendChild(history);
    return widget;
}

function createStatusItemElement(item) {
    const temp = document.createElement('div');
    temp.innerHTML = renderStatusItem(item, false);
    return temp.firstElementChild;
}

function getThinkingPreviewText(content) {
    const lines = String(content || '')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
    if (!lines.length) {
        return '';
    }
    return lines[lines.length - 1].substring(0, 150);
}

function setThinkingPreviewLine(widget, content) {
    if (!widget) return;

    const previewText = getThinkingPreviewText(content);
    let previewLine = widget.querySelector('.thinking-preview-line');

    if (!previewText) {
        if (previewLine && !String(content || '').length) {
            previewLine.style.display = 'none';
        }
        return;
    }

    if (!previewLine) {
        previewLine = document.createElement('div');
        previewLine.className = 'thinking-preview-line';
        const header = widget.querySelector('.unified-status-header');
        if (header) header.after(previewLine);
    }

    previewLine.onclick = () => {
        setStatusWidgetExpanded(
            widget.dataset.requestId || 'legacy',
            !widget.classList.contains('expanded'),
        );
    };

    previewLine.textContent = previewText;
    previewLine.style.display = 'block';
}

function syncThinkingContent(requestId) {
    const state = getStatusState(requestId);
    let widget = document.getElementById(
        getStatusWidgetDomId(requestId)
    );
    if (!widget) {
        widget = getOrCreateStatusWidget(requestId);
    }
    if (!widget) return;

    const thinkingItemId = getThinkingItemId(requestId);
    const thinkingItem = state.items.find((item) => item.id === thinkingItemId);
    if (!thinkingItem) return;

    thinkingItem.content = state.currentThinkingContent;
    setThinkingPreviewLine(widget, state.currentThinkingContent);

    const selectorId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
        ? CSS.escape(thinkingItemId)
        : thinkingItemId.replace(/"/g, '\\"');
    const element = widget.querySelector(`.status-item[data-id="${selectorId}"]`);
    if (element) {
        const updatedElement = updateStatusElement(element, thinkingItem);
        if (state.expanded) {
            scrollThinkingContentToBottom(updatedElement);
        }
    }
}

/**
 * Create a thinking block element for displaying saved thinking content.
 * @param {string} thinkingContent - The thinking content to display
 * @param {number|string} messageId - The associated message ID
 * @returns {HTMLElement} The thinking block element
 */
function createThinkingElement(thinkingContent, messageId) {
    const thinkingElement = document.createElement('div');
    thinkingElement.className = 'thinking-block thinking-done';
    thinkingElement.dataset.messageId = messageId;

    // Escape HTML in thinking content
    const escapedContent = thinkingContent
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');

    thinkingElement.innerHTML = `
        <div class="thinking-header" onclick="toggleThinkingBlockById(this)">
            <span class="thinking-icon">🧠</span>
            <span class="thinking-header-text">Thought</span>
            <span class="thinking-expand-icon">▶</span>
        </div>
        <div class="thinking-content" style="display: none;">${escapedContent}</div>
    `;

    return thinkingElement;
}

/**
 * Create a tool status element for displaying saved tool usage.
 * @param {string} toolId - The tool ID
 * @param {string} toolName - The tool name
 * @param {string} query - The query used with the tool
 * @param {string} status - The status ('completed', 'starting', etc.)
 * @param {string|null} details - Optional details (e.g., domain names)
 * @returns {HTMLElement} The tool status element
 */
function createToolStatusElement(toolId, toolName, query, status, details = null) {
    const toolElement = document.createElement('div');
    toolElement.id = `tool-status-${toolId}`;
    toolElement.className = 'tool-status tool-status-completed';
    toolElement.dataset.toolName = toolName;

    const displayName = getToolDisplayName(toolName);
    const queryPreview = query && query.length > 50 ? query.substring(0, 50) + '...' : (query || '');

    const line1 = document.createElement('div');
    line1.className = 'tool-status-line tool-status-completed';
    const check1 = document.createElement('span');
    check1.className = 'tool-checkmark';
    check1.textContent = '✅';
    const text1 = document.createElement('span');
    text1.className = 'tool-text';
    text1.textContent = `${displayName}${queryPreview ? ` for "${queryPreview}"` : ''}`;
    line1.appendChild(check1);
    line1.appendChild(text1);
    toolElement.appendChild(line1);

    if (details && String(details).trim()) {
        const line2 = document.createElement('div');
        line2.className = 'tool-status-line tool-status-completed';
        const check2 = document.createElement('span');
        check2.className = 'tool-checkmark';
        check2.textContent = '✅';
        const text2 = document.createElement('span');
        text2.className = 'tool-text tool-details';
        text2.textContent = String(details);
        line2.appendChild(check2);
        line2.appendChild(text2);
        toolElement.appendChild(line2);
    }
    return toolElement;
}

/**
 * Toggle a thinking block by clicking its header.
 * Works for both saved thinking blocks (with data-message-id) and active ones.
 * @param {HTMLElement} headerElement - The clicked header element
 */
function toggleThinkingBlockById(headerElement) {
    // Legacy function - now handled by unified widget
    const thinkingItem = headerElement.closest('.status-item.thinking-item');
    if (thinkingItem) {
        thinkingItem.classList.toggle('expanded');
    }
}

function getToolDisplayName(toolName) {
    const names = {
        'search_web': 'Searching the web',
        'search_news': 'Searching news',
        'scrape_website': 'Scraping website',
        'rag_search': 'Searching documents',
        'generate_image': 'Generating image',
        'clear_canvas': 'Clearing canvas',
        'open_image': 'Opening image',
        'save_data': 'Saving data',
        'load_data': 'Loading data',
        'record_knowledge': 'Recording knowledge',
        'recall_knowledge': 'Recalling knowledge',
    };
    return names[toolName] || `Using ${toolName}`;
}

// Unified Status Widget State
const statusWidgets = new Map();

function getStatusRequestId(requestId) {
    return requestId || 'legacy';
}

function getThinkingItemId(requestId) {
    return `thinking-current-${getStatusRequestId(requestId)}`;
}

function getStatusState(requestId) {
    const key = getStatusRequestId(requestId);
    if (!statusWidgets.has(key)) {
        statusWidgets.set(key, {
            requestId: key,
            items: [],
            maxVisible: STATUS_WIDGET_MAX_VISIBLE,
            expanded: false,
            thinkingAnimationInterval: null,
            thinkingDotCount: 0,
            currentThinkingContent: '',
            pendingThinkingRender: null,
        });
    }
    return statusWidgets.get(key);
}

function getStatusWidgetDomId(requestId) {
    return `unified-status-widget-${getStatusRequestId(requestId)}`;
}

function setStatusWidgetExpanded(requestId, expanded) {
    const state = getStatusState(requestId);
    state.expanded = !!expanded;

    const widget = document.getElementById(
        getStatusWidgetDomId(requestId)
    );
    if (widget) {
        widget.classList.toggle('expanded', state.expanded);
        if (state.expanded) {
            widget.querySelectorAll('.status-item.thinking-item').forEach(
                (element) => scrollThinkingContentToBottom(element)
            );
        }
    }

    if (state.expanded) {
        disableAutoScroll();
        return;
    }

    const container = document.getElementById('conversation-container');
    if (container && isScrolledToBottom(container)) {
        enableAutoScroll();
    }
}

function getRequestSelectorValue(requestId) {
    const key = getStatusRequestId(requestId);
    if (window.CSS && typeof window.CSS.escape === 'function') {
        return window.CSS.escape(key);
    }
    return key.replace(/"/g, '\\"');
}

function findStatusWidgetAnchor(container, requestId) {
    const key = getStatusRequestId(requestId);
    if (key === 'legacy') {
        return null;
    }

    const selectorValue = getRequestSelectorValue(requestId);
    const messages = container.querySelectorAll(`.message[data-request-id="${selectorValue}"]`);
    if (!messages.length) {
        return null;
    }

    const assistantMessage = Array.from(messages).find((message) => (
        message.classList.contains('assistant')
    ));
    if (assistantMessage) {
        return { element: assistantMessage, before: true };
    }

    return { element: messages[messages.length - 1], before: false };
}

function getOrCreateStatusWidget(requestId) {
    const container = document.getElementById('conversation-container');
    if (!container) return null;

    const state = getStatusState(requestId);
    const domId = getStatusWidgetDomId(requestId);
    let widget = document.getElementById(domId);

    if (!widget) {
        widget = document.createElement('div');
        widget.id = domId;
        widget.dataset.requestId = state.requestId;
        widget.className = 'unified-status-widget';
        widget.innerHTML = `
            <div class="unified-status-header">
                <span class="unified-status-icon">⚙️</span>
                <span class="unified-status-title">Status</span>
                <span class="unified-status-count"></span>
                <span class="unified-status-expand">▶</span>
            </div>
            <div class="unified-status-visible"></div>
            <div class="unified-status-history"></div>
        `;
        const header = widget.querySelector('.unified-status-header');
        if (header) {
            header.addEventListener('click', () => {
                setStatusWidgetExpanded(
                    requestId,
                    !getStatusState(requestId).expanded,
                );
            });
        }
        widget.addEventListener('click', (event) => {
            const copyButton = event.target.closest(
                '.status-item-copy-toggle'
            );
            if (copyButton) {
                event.stopPropagation();
                copyStatusItemText(
                    widget.dataset.requestId || 'legacy',
                    copyButton.dataset.itemId || '',
                );
                return;
            }
            const toggle = event.target.closest(
                '.status-item-metadata-toggle'
            );
            if (!toggle) {
                return;
            }
            event.stopPropagation();
            toggleStatusItemMetadata(
                widget.dataset.requestId || 'legacy',
                toggle.dataset.itemId || '',
            );
        });
    }

    const anchor = findStatusWidgetAnchor(container, requestId);
    if (anchor) {
        if (anchor.before) {
            container.insertBefore(widget, anchor.element);
        } else {
            anchor.element.insertAdjacentElement('afterend', widget);
        }
    } else if (widget.parentElement !== container) {
        container.appendChild(widget);
    } else if (!widget.parentElement) {
        container.appendChild(widget);
    }

    return widget;
}

function toggleStatusWidget() {
    const widget = document.querySelector('.unified-status-widget');
    if (widget) {
        setStatusWidgetExpanded(
            widget.dataset.requestId || 'legacy',
            !widget.classList.contains('expanded'),
        );
    }
}

function addStatusItem(requestId, item) {
    const state = getStatusState(requestId);
    item.timestamp = Date.now();

    const existingIndex = state.items.findIndex((existingItem) => (
        existingItem.id === item.id
    ));
    if (existingIndex >= 0) {
        state.items[existingIndex] = { ...state.items[existingIndex], ...item };
    } else {
        state.items.unshift(item);
    }

    renderStatusWidget(requestId);
}

function updateStatusItem(requestId, id, updates) {
    const state = getStatusState(requestId);
    const item = state.items.find((existingItem) => existingItem.id === id);
    if (!item) {
        return;
    }

    Object.assign(item, updates);
    renderStatusWidget(requestId);
}

function removeStatusItem(requestId, id) {
    const state = getStatusState(requestId);
    const nextItems = state.items.filter((item) => item.id !== id);
    if (nextItems.length === state.items.length) {
        return;
    }
    state.items = nextItems;
    renderStatusWidget(requestId);
}

function removeStatusWidget(requestId) {
    const domId = getStatusWidgetDomId(requestId);
    const widget = document.getElementById(domId);
    if (widget) {
        widget.remove();
    }
}

function renderStatusWidget(requestId) {
    const state = getStatusState(requestId);
    if (!state.items.length) {
        removeStatusWidget(requestId);
        return;
    }

    const widget = getOrCreateStatusWidget(requestId);
    if (!widget) return;

    const visibleContainer = widget.querySelector('.unified-status-visible');
    const historyContainer = widget.querySelector('.unified-status-history');
    const countSpan = widget.querySelector('.unified-status-count');
    const titleSpan = widget.querySelector('.unified-status-title');
    const iconSpan = widget.querySelector('.unified-status-icon');

    if (!visibleContainer || !historyContainer) return;

    const hasThinking = state.items.some((item) => item.type === 'thinking');
    widget.classList.toggle('has-thinking', hasThinking);
    widget.classList.toggle('expanded', !!state.expanded);

    const activeItems = state.items.filter((item) => item.status === 'active');
    if (activeItems.length > 0) {
        const activeItem = activeItems[0];
        const isThinking = activeItem.type === 'thinking';
        const isModelLoading = activeItem.type === 'model_loading';
        const newIcon = isThinking ? '🧠' : (isModelLoading ? '⏳' : '⚙️');
        const baseTitle = isThinking
            ? 'Thinking'
            : (isModelLoading ? activeItem.text : 'Working...');
        if (iconSpan.textContent !== newIcon) iconSpan.textContent = newIcon;

        if (isThinking || isModelLoading) {
            titleSpan.textContent = baseTitle;
            titleSpan.classList.add('animated-dots');
        } else {
            if (titleSpan.textContent !== baseTitle) titleSpan.textContent = baseTitle;
            titleSpan.classList.remove('animated-dots');
        }
        iconSpan.classList.add('pulsing');

    } else {
        if (iconSpan.textContent !== '✅') iconSpan.textContent = '✅';
        if (titleSpan.textContent !== 'Completed') titleSpan.textContent = 'Completed';
        titleSpan.classList.remove('animated-dots');
        iconSpan.classList.remove('pulsing');
    }

    const thinkingItem = state.items.find((item) => (
        item.type === 'thinking' && item.content
    ));
    setThinkingPreviewLine(widget, thinkingItem ? thinkingItem.content : '');

    const newCount = state.items.length > state.maxVisible
        ? `${state.items.length} items`
        : '';
    if (countSpan.textContent !== newCount) countSpan.textContent = newCount;

    updateStatusContainer(
        visibleContainer,
        state.items.slice(0, state.maxVisible),
    );
    updateStatusContainer(
        historyContainer,
        state.items.slice(state.maxVisible),
    );

    if (window.autoScrollEnabled && !state.expanded) {
        setTimeout(smoothScrollToBottom, 0);
    }
}

/**
 * Smart DOM update - only update what changed instead of replacing innerHTML
 */
function updateStatusContainer(container, items) {
    const existingElements = container.querySelectorAll('.status-item');
    const existingIds = new Set();

    // Build map of existing elements
    existingElements.forEach(el => {
        existingIds.add(el.dataset.id);
    });

    // Track which items we've processed
    const itemIds = new Set(items.map(i => i.id));

    // Remove elements that are no longer in items
    existingElements.forEach(el => {
        if (!itemIds.has(el.dataset.id)) {
            el.remove();
        }
    });

    // Update or add items
    items.forEach((item, index) => {
        let element = container.querySelector(`.status-item[data-id="${item.id}"]`);

        if (element) {
            element = updateStatusElement(element, item);
        } else {
            // Create new element
            const html = renderStatusItem(item, true); // true = new item
            const temp = document.createElement('div');
            temp.innerHTML = html;
            element = temp.firstElementChild;

            // Insert at correct position
            const existingAtIndex = container.children[index];
            if (existingAtIndex) {
                container.insertBefore(element, existingAtIndex);
            } else {
                container.appendChild(element);
            }
        }

        if (item.type === 'thinking' && item.content) {
            scrollThinkingContentToBottom(element);
        }
    });
}

function scrollThinkingContentToBottom(element) {
    if (!element) return;

    const wrapper = element.querySelector('.thinking-content-wrapper');
    if (!wrapper) return;

    const inner = wrapper.querySelector('.thinking-content-inner');
    requestAnimationFrame(() => {
        wrapper.scrollTop = wrapper.scrollHeight;
        if (inner) {
            inner.scrollTop = inner.scrollHeight;
        }
    });
}

/**
 * Re-render one status item and replace its DOM node in place.
 */
function updateStatusElement(element, item) {
    const temp = document.createElement('div');
    temp.innerHTML = renderStatusItem(item);
    const nextElement = temp.firstElementChild;
    if (!nextElement) {
        return element;
    }
    element.replaceWith(nextElement);
    return nextElement;
}

function parseStatusMetadata(metadataJson) {
    if (!metadataJson) {
        return null;
    }
    try {
        return JSON.parse(metadataJson);
    } catch (error) {
        console.warn(
            '[conversation.js] Failed to parse thinking metadata:',
            error,
        );
        return null;
    }
}

function formatStatusMetadataLabel(label) {
    return String(label)
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatStatusMetadataValue(value) {
    if (value === null || value === undefined) {
        return '';
    }
    if (typeof value === 'object') {
        return JSON.stringify(value);
    }
    return String(value);
}

function renderStatusMetadataPanel(item) {
    if (!item.metadata || !item.metadataExpanded) {
        return '';
    }

    let rows = '';
    [['stage', 'Stage'], ['intent', 'Intent'], ['preset_id', 'Preset']]
        .forEach(([fieldName, label]) => {
            const value = item.metadata[fieldName];
            if (!value) {
                return;
            }
            rows += `
                <div class="status-item-metadata-row">
                    <span class="status-item-metadata-key">${escapeHtml(label)}</span>
                    <span class="status-item-metadata-value">${escapeHtml(String(value))}</span>
                </div>
            `;
        });

    Object.entries(item.metadata.settings || {}).forEach(([key, value]) => {
        rows += `
            <div class="status-item-metadata-row">
                <span class="status-item-metadata-key">${escapeHtml(formatStatusMetadataLabel(key))}</span>
                <span class="status-item-metadata-value">${escapeHtml(formatStatusMetadataValue(value))}</span>
            </div>
        `;
    });

    return `
        <div class="status-item-metadata-panel">
            <div class="status-item-metadata-title">${escapeHtml(item.metadata.title || 'Generation Settings')}</div>
            ${rows}
        </div>
    `;
}

function toggleStatusItemMetadata(requestId, itemId) {
    if (!itemId) {
        return;
    }
    const state = getStatusState(requestId);
    const item = state.items.find((existingItem) => existingItem.id === itemId);
    if (!item || !item.metadata) {
        return;
    }
    item.metadataExpanded = !item.metadataExpanded;
    renderStatusWidget(requestId);
}

function buildStatusItemCopyText(item) {
    if (!item) {
        return '';
    }

    const sections = [];
    const statusText = String(item.text || '').trim();
    if (statusText) {
        sections.push(statusText);
    }

    const contentText = String(item.content || '').trim();
    if (contentText) {
        sections.push(contentText);
    }

    if (item.metadata) {
        const metadataLines = [];
        [['stage', 'Stage'], ['intent', 'Intent'], ['preset_id', 'Preset']]
            .forEach(([fieldName, label]) => {
                const value = item.metadata[fieldName];
                if (!value) {
                    return;
                }
                metadataLines.push(
                    `${label}: ${formatStatusMetadataValue(value)}`,
                );
            });

        Object.entries(item.metadata.settings || {}).forEach(([key, value]) => {
            metadataLines.push(
                `${formatStatusMetadataLabel(key)}: ${formatStatusMetadataValue(value)}`,
            );
        });

        if (metadataLines.length) {
            const title = String(
                item.metadata.title || 'Generation Settings',
            ).trim();
            sections.push(`${title}\n${metadataLines.join('\n')}`);
        }
    }

    return sections.join('\n\n').trim();
}

function buildStatusWidgetCopyText(requestId) {
    const state = getStatusState(requestId);
    return state.items
        .map((item) => buildStatusItemCopyText(item))
        .filter((text) => !!text)
        .join('\n\n');
}

function copyStatusText(text) {
    const normalized = String(text || '');
    if (!normalized) {
        return;
    }
    if (window.chatBridge && typeof window.chatBridge.copyText === 'function') {
        window.chatBridge.copyText(normalized);
        return;
    }
    copyTextToClipboard(normalized).catch((error) => {
        console.warn('[conversation.js] failed to copy thinking text:', error);
    });
}

function buildSavedStatusWidgetCopyText(items) {
    return (items || [])
        .map((item) => buildStatusItemCopyText(item))
        .filter((text) => !!text)
        .join('\n\n');
}

function copyStatusItemText(requestId, itemId) {
    if (!itemId) {
        return;
    }
    const state = getStatusState(requestId);
    const item = state.items.find((existingItem) => existingItem.id === itemId);
    const text = item && item.type === 'thinking'
        ? buildStatusWidgetCopyText(requestId)
        : buildStatusItemCopyText(item);
    if (!text) {
        return;
    }
    copyStatusText(text);
}

function renderStatusItem(item, isNew = false) {
    const isActive = item.status === 'active';
    const icon = item.type === 'thinking'
        ? (isActive ? '🧠' : '💭')
        : (item.type === 'model_loading'
            ? (isActive ? '⏳' : '✅')
            : (isActive ? '⏳' : '✅'));

    const classes = [
        'status-item',
        `${item.type}-item`,
        isActive ? 'active' : 'completed',
        isNew ? 'new-item' : '',
        item.expanded ? 'expanded' : '',
        item.metadataExpanded ? 'metadata-expanded' : ''
    ].filter(Boolean).join(' ');

    const metadataToggle = item.metadata
        ? `
            <button
                class="status-item-metadata-toggle"
                type="button"
                data-item-id="${escapeAttr(item.id)}"
                aria-expanded="${item.metadataExpanded ? 'true' : 'false'}"
                title="${escapeAttr(
                    item.metadataExpanded
                        ? 'Hide generation settings'
                        : 'Show generation settings'
                )}"
            >
                ⚙
            </button>
        `
        : '';

    const copyText = item.type === 'thinking'
        ? 'widget'
        : '';
    const copyToggle = item.type === 'thinking'
        ? `
            <button
                class="status-item-copy-toggle"
                type="button"
                data-item-id="${escapeAttr(item.id)}"
                title="${escapeAttr(
                    copyText
                        ? 'Copy thinking widget text'
                        : 'No thinking text to copy yet'
                )}"
                aria-label="${escapeAttr(
                    copyText
                        ? 'Copy thinking widget text'
                        : 'No thinking text to copy yet'
                )}"
                ${copyText ? '' : 'disabled'}
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
            </button>
        `
        : '';

    const actionButtons = (copyToggle || metadataToggle)
        ? `
            <span class="status-item-actions">
                ${copyToggle}
                ${metadataToggle}
            </span>
        `
        : '';

    let html = `
        <div class="${classes}" data-id="${escapeAttr(item.id)}">
            <div class="status-item-main">
                <span class="status-item-icon ${isActive ? 'spinning' : ''}">${icon}</span>
                <span class="status-item-text">${escapeHtml(item.text)}</span>
                ${actionButtons}
            </div>
    `;

    // Add expandable thinking content
    if (item.type === 'thinking' && item.content) {
        html += `
            <div class="thinking-content-wrapper">
                <div class="thinking-content-inner">${escapeHtml(item.content)}</div>
            </div>
        `;
    }

    html += renderStatusMetadataPanel(item);

    html += '</div>';
    return html;
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

function escapeAttr(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function clearStatusWidgets() {
    statusWidgets.forEach((state) => {
        if (state.thinkingAnimationInterval) {
            clearInterval(state.thinkingAnimationInterval);
        }
        if (state.pendingThinkingRender) {
            clearTimeout(state.pendingThinkingRender);
        }
    });
    statusWidgets.clear();
    document.querySelectorAll('.unified-status-widget').forEach((widget) => {
        widget.remove();
    });
}

function startThinkingAnimation(requestId) {
    const state = getStatusState(requestId);
    if (state.thinkingAnimationInterval) {
        clearInterval(state.thinkingAnimationInterval);
        state.thinkingAnimationInterval = null;
    }
}

function stopThinkingAnimation(requestId) {
    const state = getStatusState(requestId);
    if (!state.thinkingAnimationInterval) {
        return;
    }
    clearInterval(state.thinkingAnimationInterval);
    state.thinkingAnimationInterval = null;
}

function flushThinkingRender(requestId) {
    const state = getStatusState(requestId);
    if (state.pendingThinkingRender) {
        clearTimeout(state.pendingThinkingRender);
        state.pendingThinkingRender = null;
    }
    syncThinkingContent(requestId);
}

function scheduleThinkingRender(requestId) {
    const state = getStatusState(requestId);
    if (state.pendingThinkingRender) {
        return;
    }
    state.pendingThinkingRender = setTimeout(() => {
        state.pendingThinkingRender = null;
        syncThinkingContent(requestId);
    }, 75);
}

function handleThinkingStatusUpdate(requestId, status, content, metadataJson) {
    const state = getStatusState(requestId);
    const thinkingItemId = getThinkingItemId(requestId);
    const metadata = parseStatusMetadata(metadataJson);

    if (status === 'started') {
        flushThinkingRender(requestId);
        state.currentThinkingContent = '';
        addStatusItem(requestId, {
            id: thinkingItemId,
            type: 'thinking',
            text: 'Thinking',
            status: 'active',
            content: '',
            metadata,
        });
        startThinkingAnimation(requestId);
        return;
    }

    if (status === 'streaming') {
        state.currentThinkingContent += content;
        if (metadata) {
            updateStatusItem(requestId, thinkingItemId, { metadata });
        }
        scheduleThinkingRender(requestId);
        return;
    }

    if (status === 'completed') {
        stopThinkingAnimation(requestId);
        if (content) {
            state.currentThinkingContent = content;
        }
        flushThinkingRender(requestId);
        const updates = {
            text: 'Completed',
            status: 'completed',
            content: state.currentThinkingContent,
        };
        if (metadata) {
            updates.metadata = metadata;
        }
        updateStatusItem(requestId, thinkingItemId, updates);
    }
}

function handleModelLoadStatusUpdate(requestId, status, message) {
    const itemId = `model-loading-${getStatusRequestId(requestId)}`;
    if (status === 'started') {
        addStatusItem(requestId, {
            id: itemId,
            type: 'model_loading',
            text: message || 'Loading model',
            status: 'active'
        });
        return;
    }
    removeStatusItem(requestId, itemId);
}

// Keep for backwards compatibility
function toggleThinkingBlock() {
    const widget = document.querySelector('.unified-status-widget');
    if (widget) {
        setStatusWidgetExpanded(
            widget.dataset.requestId || 'legacy',
            !widget.classList.contains('expanded'),
        );
    }
}

function handleToolStatusUpdate(requestId, toolId, toolName, query, status, details, metadataJson) {
    const displayName = getToolDisplayName(toolName);
    const queryPreview = query.length > 50 ? query.substring(0, 50) + '...' : query;
    const text = `${displayName} for "${queryPreview}"`;
    const itemId = `tool-${getStatusRequestId(requestId)}-${toolId}`;
    const metadata = parseStatusMetadata(metadataJson);

    if (status === 'starting') {
        addStatusItem(requestId, {
            id: itemId,
            type: 'tool',
            text: text,
            status: 'active',
            metadata,
        });
    } else if (status === 'completed') {
        const updates = {
            text: text + (details ? ` - ${details}` : ''),
            status: 'completed',
        };
        if (metadata) {
            updates.metadata = metadata;
        }
        updateStatusItem(requestId, itemId, updates);
    }
}

function removeToolStatusesForTool(toolName, activeElementId) {
    // Legacy function - now handled by unified widget
    if (!toolName) return;
    statusWidgets.forEach((state, requestId) => {
        state.items = state.items.filter((item) => {
            if (item.type !== 'tool') return true;
            if (item.id === activeElementId) return true;
            return !item.text.toLowerCase().includes(toolName.toLowerCase());
        });
        renderStatusWidget(requestId);
    });
}

function clearMessagesKeepToolStatus() {
    const container = document.getElementById('conversation-container');
    if (!container) {
        console.log('[TOOL STATUS DEBUG] Container not found');
        return;
    }

    const widgets = Array.from(
        container.querySelectorAll('.unified-status-widget')
    );
    container.innerHTML = '';

    widgets.forEach((widget) => {
        const requestId = widget.dataset.requestId || 'legacy';
        const state = statusWidgets.get(requestId);
        if (state && state.items.length > 0) {
            container.appendChild(widget);
        }
    });
}

function clearMessages() {
    console.log('[TOOL STATUS DEBUG] clearMessages called - clearing everything');
    clearStatusWidgets();
    const container = document.getElementById('conversation-container');
    if (container) container.innerHTML = '';
}

function smoothScrollToBottom() {
    const container = document.getElementById('conversation-container');
    if (container) {
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
            requestAnimationFrame(() => {
                container.scrollTop = container.scrollHeight;
            });
            if (isScrolledToBottom(container)) enableAutoScroll();
            const contentHeight = container.scrollHeight;
            if (window.isChatReady && window.chatBridge && typeof window.chatBridge.update_content_height === 'function') {
                window.chatBridge.update_content_height(contentHeight);
            } else if (!window.isChatReady || !window.chatBridge) {
                setTimeout(smoothScrollToBottom, 100);
            }
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatView);
} else {
    initializeChatView();
}
