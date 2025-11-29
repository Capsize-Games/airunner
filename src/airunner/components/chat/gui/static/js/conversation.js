// conversation.js: Minimal chat widget logic with MathJax integration

let chatBridge = null;
window.isChatReady = false;
window.chatReady = new Promise((resolve) => {
    window.chatReadyResolve = resolve;
});
window.autoScrollEnabled = true;

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
        chatBridge.updateLastMessageContent.connect(function (content) {
            // Update only the last message's content during streaming
            const container = document.getElementById('conversation-container');
            if (!container) return;

            // Find all message divs (exclude tool status)
            const messages = container.querySelectorAll('.message:not(.tool-status):not(.thinking-block)');
            if (messages.length === 0) return;

            const lastMessage = messages[messages.length - 1];
            const contentDiv = lastMessage.querySelector('.content');
            if (!contentDiv) return;

            // Update content with sanitized HTML
            contentDiv.innerHTML = sanitizeContent(content);

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

function sanitizeContent(html) {
    // Content is already formatted HTML from FormatterExtended on the backend
    // Just unescape if it's a JSON string, then return as-is
    let content = html;

    if (typeof content === 'string') {
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
        // This prevents blank space at the start/end of messages
        content = content
            .replace(/^(\s*<(p|div|br)[^>]*>\s*<\/(p|div)>\s*)+/gi, '')  // Leading empty block elements
            .replace(/(\s*<(p|div|br)[^>]*>\s*<\/(p|div)>\s*)+$/gi, '')  // Trailing empty block elements
            .replace(/^(<br\s*\/?>)+/gi, '')  // Leading <br> tags
            .replace(/(<br\s*\/?>)+$/gi, '')  // Trailing <br> tags
            .replace(/^\s+/, '')  // Leading whitespace
            .replace(/\s+$/, ''); // Trailing whitespace
    }

    return content;
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
    const senderDiv = document.createElement('div');
    senderDiv.className = 'sender';
    senderDiv.textContent = msg.name || msg.sender || (msg.is_bot ? 'Assistant' : 'User');

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.innerHTML = sanitizeContent(msg.content);

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
                    if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                        navigator.clipboard.writeText(text).catch(() => { });
                    } else {
                        const ta = document.createElement('textarea');
                        ta.value = text;
                        document.body.appendChild(ta);
                        ta.select();
                        document.execCommand('copy');
                        document.body.removeChild(ta);
                    }
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

    // For assistant messages, render widgets in the correct order:
    // 1. Pre-tool thinking (if present)
    // 2. Tool status widgets (if present)
    // 3. Post-tool thinking (if present, or regular thinking)
    // 4. Message content

    if (msg.is_bot) {
        // 1. Render pre-tool thinking block first (thinking before tool use)
        if (msg.pre_tool_thinking) {
            console.log(`[appendMessage] Rendering pre_tool_thinking for msg ${msg.id}`);
            const preThinkingElement = createThinkingElement(msg.pre_tool_thinking, `${msg.id}-pre`);
            container.appendChild(preThinkingElement);
        }

        // 2. Render tool status widgets
        if (msg.tool_usage && Array.isArray(msg.tool_usage)) {
            console.log(`[appendMessage] Rendering ${msg.tool_usage.length} tool widgets for msg ${msg.id}`);
            for (const tool of msg.tool_usage) {
                const toolElement = createToolStatusElement(
                    tool.tool_id || `saved-tool-${msg.id}-${tool.tool_name}`,
                    tool.tool_name,
                    tool.query,
                    'completed',  // Saved tool usages are always completed
                    tool.details || null  // Include details (domains) if present
                );
                container.appendChild(toolElement);
            }
        }

        // 3. Render post-tool thinking block (thinking after tool results)
        if (msg.thinking_content) {
            console.log(`[appendMessage] Rendering thinking_content for msg ${msg.id}`);
            const thinkingElement = createThinkingElement(msg.thinking_content, msg.id);
            container.appendChild(thinkingElement);
        }
    }

    const messageElement = createMessageElement(msg);
    container.appendChild(messageElement);
    if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
        try { await window.MathJax.typesetPromise([messageElement]); } catch { }
    }
    if (scroll && window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
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

    let html = `
        <div class="tool-status-line tool-status-completed">
            <span class="tool-checkmark">✅</span>
            <span class="tool-text">${displayName}${queryPreview ? ` for "${queryPreview}"` : ''}</span>
        </div>
    `;

    // Add details line if present (e.g., domain names from search results)
    if (details && details.trim()) {
        html += `
            <div class="tool-status-line tool-status-completed">
                <span class="tool-checkmark">✅</span>
                <span class="tool-text tool-details">${details}</span>
            </div>
        `;
    }

    toolElement.innerHTML = html;
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
const statusWidget = {
    items: [],           // All status items {id, type, text, status, content?, timestamp}
    maxVisible: 2,       // Max items shown without expanding
    animationTimeout: null
};

function getOrCreateStatusWidget() {
    const container = document.getElementById('conversation-container');
    if (!container) return null;

    let widget = document.getElementById('unified-status-widget');
    if (!widget) {
        widget = document.createElement('div');
        widget.id = 'unified-status-widget';
        widget.className = 'unified-status-widget';
        widget.innerHTML = `
            <div class="unified-status-header" onclick="toggleStatusWidget()">
                <span class="unified-status-icon">⚙️</span>
                <span class="unified-status-title">Status</span>
                <span class="unified-status-count"></span>
                <span class="unified-status-expand">▶</span>
            </div>
            <div class="unified-status-visible"></div>
            <div class="unified-status-history"></div>
        `;

        // Insert before last assistant message or append
        const messages = container.querySelectorAll('.message:not(.tool-status):not(.thinking-block):not(.unified-status-widget)');
        const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;

        if (lastMessage && lastMessage.classList.contains('assistant')) {
            container.insertBefore(widget, lastMessage);
        } else {
            container.appendChild(widget);
        }
    }
    return widget;
}

function toggleStatusWidget() {
    const widget = document.getElementById('unified-status-widget');
    if (!widget) return;
    widget.classList.toggle('expanded');
}

function addStatusItem(item) {
    // item: {id, type: 'thinking'|'tool', text, status: 'active'|'completed', content?: string}
    item.timestamp = Date.now();

    // Check if this item already exists
    const existingIndex = statusWidget.items.findIndex(i => i.id === item.id);
    if (existingIndex >= 0) {
        // Update existing item
        statusWidget.items[existingIndex] = { ...statusWidget.items[existingIndex], ...item };
    } else {
        // Add new item at the beginning
        statusWidget.items.unshift(item);
    }

    renderStatusWidget();
}

function updateStatusItem(id, updates) {
    const item = statusWidget.items.find(i => i.id === id);
    if (item) {
        Object.assign(item, updates);
        renderStatusWidget();
    }
}

function renderStatusWidget() {
    const widget = getOrCreateStatusWidget();
    if (!widget) return;

    const visibleContainer = widget.querySelector('.unified-status-visible');
    const historyContainer = widget.querySelector('.unified-status-history');
    const countSpan = widget.querySelector('.unified-status-count');
    const titleSpan = widget.querySelector('.unified-status-title');
    const iconSpan = widget.querySelector('.unified-status-icon');

    if (!visibleContainer || !historyContainer) return;

    // Check if we have any thinking items
    const hasThinking = statusWidget.items.some(i => i.type === 'thinking');
    widget.classList.toggle('has-thinking', hasThinking);

    // Update header based on active items
    const activeItems = statusWidget.items.filter(i => i.status === 'active');
    if (activeItems.length > 0) {
        const activeItem = activeItems[0];
        const newIcon = activeItem.type === 'thinking' ? '🧠' : '⚙️';
        // Title will be animated via CSS for thinking, static for tools
        const baseTitle = activeItem.type === 'thinking' ? 'Thinking' : 'Working...';
        if (iconSpan.textContent !== newIcon) iconSpan.textContent = newIcon;

        // Set base title and add animated-dots class for thinking
        if (activeItem.type === 'thinking') {
            titleSpan.textContent = baseTitle;
            titleSpan.classList.add('animated-dots');
        } else {
            if (titleSpan.textContent !== baseTitle) titleSpan.textContent = baseTitle;
            titleSpan.classList.remove('animated-dots');
        }
        iconSpan.classList.add('pulsing');

        // Show streaming thinking content in preview line
        const thinkingItem = statusWidget.items.find(i => i.type === 'thinking' && i.content);
        let previewLine = widget.querySelector('.thinking-preview-line');
        if (thinkingItem && thinkingItem.content) {
            if (!previewLine) {
                previewLine = document.createElement('div');
                previewLine.className = 'thinking-preview-line';
                const header = widget.querySelector('.unified-status-header');
                if (header) header.after(previewLine);
            }
            // Get last line of thinking content
            const lines = thinkingItem.content.trim().split('\n');
            const lastLine = lines[lines.length - 1] || '';
            previewLine.textContent = lastLine.substring(0, 150);
            previewLine.style.display = 'block';
        } else if (previewLine) {
            previewLine.style.display = 'none';
        }
    } else if (statusWidget.items.length > 0) {
        if (iconSpan.textContent !== '✅') iconSpan.textContent = '✅';
        if (titleSpan.textContent !== 'Completed') titleSpan.textContent = 'Completed';
        titleSpan.classList.remove('animated-dots');
        iconSpan.classList.remove('pulsing');

        // Hide preview line when completed
        const previewLine = widget.querySelector('.thinking-preview-line');
        if (previewLine) previewLine.style.display = 'none';
    }

    // Update count
    const newCount = statusWidget.items.length > statusWidget.maxVisible
        ? `${statusWidget.items.length} items`
        : '';
    if (countSpan.textContent !== newCount) countSpan.textContent = newCount;

    // Update visible items using smart DOM diffing
    const visibleItems = statusWidget.items.slice(0, statusWidget.maxVisible);
    updateStatusContainer(visibleContainer, visibleItems);

    // Update history items
    const historyItems = statusWidget.items.slice(statusWidget.maxVisible);
    updateStatusContainer(historyContainer, historyItems);

    if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
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
            // Update existing element in place
            updateStatusElement(element, item);
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
    });
}

/**
 * Update an existing status element in place without recreating it
 */
function updateStatusElement(element, item) {
    const isActive = item.status === 'active';
    const icon = item.type === 'thinking'
        ? (isActive ? '🧠' : '💭')
        : (isActive ? '⏳' : '✅');

    // Update classes
    element.classList.toggle('active', isActive);
    element.classList.toggle('completed', !isActive);
    element.classList.remove('new-item'); // Remove animation class after first render

    // Update icon
    const iconEl = element.querySelector('.status-item-icon');
    if (iconEl) {
        if (iconEl.textContent !== icon) iconEl.textContent = icon;
        iconEl.classList.toggle('spinning', isActive);
    }

    // Update text
    const textEl = element.querySelector('.status-item-text');
    if (textEl && textEl.textContent !== item.text) {
        textEl.textContent = item.text;
    }

    // Update thinking content if present
    if (item.type === 'thinking' && item.content) {
        let wrapper = element.querySelector('.thinking-content-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'thinking-content-wrapper';
            wrapper.innerHTML = '<div class="thinking-content-inner"></div>';
            element.appendChild(wrapper);
        }
        const inner = wrapper.querySelector('.thinking-content-inner');
        if (inner) {
            inner.innerHTML = escapeHtml(item.content);
        }
    }
}

function renderStatusItem(item, isNew = false) {
    const isActive = item.status === 'active';
    const icon = item.type === 'thinking'
        ? (isActive ? '🧠' : '💭')
        : (isActive ? '⏳' : '✅');

    const classes = [
        'status-item',
        `${item.type}-item`,
        isActive ? 'active' : 'completed',
        isNew ? 'new-item' : '',
        item.expanded ? 'expanded' : ''
    ].filter(Boolean).join(' ');

    let html = `
        <div class="${classes}" data-id="${item.id}">
            <span class="status-item-icon ${isActive ? 'spinning' : ''}">${icon}</span>
            <span class="status-item-text">${item.text}</span>
    `;

    // Add expandable thinking content
    if (item.type === 'thinking' && item.content) {
        html += `
            <div class="thinking-content-wrapper">
                <div class="thinking-content-inner">${escapeHtml(item.content)}</div>
            </div>
        `;
    }

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

function clearStatusWidget() {
    statusWidget.items = [];
    const widget = document.getElementById('unified-status-widget');
    if (widget) {
        widget.remove();
    }
}

// Track thinking animation state
let thinkingAnimationInterval = null;
let thinkingDotCount = 0;
let currentThinkingContent = '';

function startThinkingAnimation() {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
    }
    thinkingDotCount = 0;

    thinkingAnimationInterval = setInterval(() => {
        thinkingDotCount = (thinkingDotCount + 1) % 4;
        const dots = '.'.repeat(thinkingDotCount);
        updateStatusItem('thinking-current', { text: `Thinking${dots}` });
    }, 400);
}

function stopThinkingAnimation() {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
        thinkingAnimationInterval = null;
    }
}

function handleThinkingStatusUpdate(status, content) {
    if (status === 'started') {
        currentThinkingContent = '';
        addStatusItem({
            id: 'thinking-current',
            type: 'thinking',
            text: 'Thinking',
            status: 'active',
            content: ''
        });
        startThinkingAnimation();

    } else if (status === 'streaming') {
        currentThinkingContent += content;
        updateStatusItem('thinking-current', { content: currentThinkingContent });

    } else if (status === 'completed') {
        stopThinkingAnimation();
        updateStatusItem('thinking-current', {
            text: 'Thought',
            status: 'completed',
            content: currentThinkingContent
        });
    }
}

// Keep for backwards compatibility
function toggleThinkingBlock() {
    const widget = document.getElementById('unified-status-widget');
    if (widget) {
        widget.classList.toggle('expanded');
    }
}

function handleToolStatusUpdate(toolId, toolName, query, status, details) {
    const displayName = getToolDisplayName(toolName);
    const queryPreview = query.length > 50 ? query.substring(0, 50) + '...' : query;
    const text = `${displayName} for "${queryPreview}"`;

    if (status === 'starting') {
        addStatusItem({
            id: `tool-${toolId}`,
            type: 'tool',
            text: text,
            status: 'active'
        });
    } else if (status === 'completed') {
        updateStatusItem(`tool-${toolId}`, {
            text: text + (details ? ` - ${details}` : ''),
            status: 'completed'
        });
    }
}

function removeToolStatusesForTool(toolName, activeElementId) {
    // Legacy function - now handled by unified widget
    // Remove items from statusWidget.items that match toolName but not activeElementId
    if (!toolName) return;
    statusWidget.items = statusWidget.items.filter(item => {
        if (item.type !== 'tool') return true;
        if (item.id === activeElementId) return true;
        // Keep if it doesn't match the tool name (approximate check)
        return !item.text.toLowerCase().includes(toolName.toLowerCase());
    });
    renderStatusWidget();
}

function clearMessagesKeepToolStatus() {
    const container = document.getElementById('conversation-container');
    if (!container) {
        console.log('[TOOL STATUS DEBUG] Container not found');
        return;
    }

    // Stop any running thinking animation since we're clearing
    stopThinkingAnimation();

    // Clear all content but preserve the unified status widget
    const widget = document.getElementById('unified-status-widget');
    container.innerHTML = '';

    if (widget && statusWidget.items.length > 0) {
        container.appendChild(widget);
    }
}

function clearMessages() {
    console.log('[TOOL STATUS DEBUG] clearMessages called - clearing everything');
    // Also stop thinking animation if running
    stopThinkingAnimation();
    // Clear status widget state
    clearStatusWidget();
    const container = document.getElementById('conversation-container');
    if (container) container.innerHTML = '';
}

function smoothScrollToBottom() {
    const container = document.getElementById('conversation-container');
    if (container) {
        requestAnimationFrame(() => {
            const lastMsg = container.lastElementChild;
            if (lastMsg) {
                lastMsg.scrollIntoView({ behavior: 'auto', block: 'end' });
            } else {
                container.scrollTop = container.scrollHeight;
            }
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
