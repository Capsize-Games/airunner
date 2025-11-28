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
            console.log(`[TOOL STATUS DEBUG] setMessages called with ${msgs.length} messages`);

            // Always preserve tool statuses when setting messages
            // Use clearMessages signal explicitly if you want to clear everything
            clearMessagesKeepToolStatus();

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
            } else {
                if (console && console.debug) console.debug('[conversation.js] auto-scroll suppressed because user scrolled up');
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
    }

    return content;
} function createMessageElement(msg) {
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

    // If this is an assistant message with thinking content, render thinking block first
    if (msg.is_bot && msg.thinking_content) {
        const thinkingElement = createThinkingElement(msg.thinking_content, msg.id);
        container.appendChild(thinkingElement);
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
 * Toggle a thinking block by clicking its header.
 * Works for both saved thinking blocks (with data-message-id) and active ones.
 * @param {HTMLElement} headerElement - The clicked header element
 */
function toggleThinkingBlockById(headerElement) {
    const thinkingElement = headerElement.closest('.thinking-block');
    if (!thinkingElement) return;

    const contentDiv = thinkingElement.querySelector('.thinking-content');
    const expandIcon = thinkingElement.querySelector('.thinking-expand-icon');

    if (!contentDiv || !expandIcon) return;

    const isExpanded = thinkingElement.classList.contains('expanded');

    if (isExpanded) {
        // Collapse
        contentDiv.style.display = 'none';
        expandIcon.textContent = '▶';
        thinkingElement.classList.remove('expanded');
    } else {
        // Expand
        contentDiv.style.display = 'block';
        expandIcon.textContent = '▼';
        thinkingElement.classList.add('expanded');

        // Scroll to show the content
        if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
    }
}

function getToolDisplayName(toolName) {
    const names = {
        'search_web': 'Searching the internet',
        'rag_search': 'Searching documents',
        'generate_image': 'Generating image',
        'clear_canvas': 'Clearing canvas',
        'open_image': 'Opening image',
        'save_data': 'Saving data',
        'load_data': 'Loading data',
    };
    return names[toolName] || `Using ${toolName}`;
}

// Track thinking animation state
let thinkingAnimationInterval = null;
let thinkingDotCount = 0;

function startThinkingAnimation(element) {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
    }
    thinkingDotCount = 0;
    const textSpan = element.querySelector('.thinking-header-text');
    if (!textSpan) return;

    thinkingAnimationInterval = setInterval(() => {
        thinkingDotCount = (thinkingDotCount + 1) % 4;
        const dots = '.'.repeat(thinkingDotCount);
        textSpan.textContent = `Thinking${dots}`;
    }, 400);
}

function stopThinkingAnimation() {
    if (thinkingAnimationInterval) {
        clearInterval(thinkingAnimationInterval);
        thinkingAnimationInterval = null;
    }
}

function handleThinkingStatusUpdate(status, content) {
    console.log('[THINKING DEBUG] handleThinkingStatusUpdate called:', { status, contentLen: content.length });

    const container = document.getElementById('conversation-container');
    if (!container) {
        console.log('[THINKING DEBUG] Container not found');
        return;
    }

    const thinkingElementId = 'thinking-block-current';
    let thinkingElement = document.getElementById(thinkingElementId);

    if (status === 'started') {
        // Remove any existing thinking block
        if (thinkingElement) {
            thinkingElement.remove();
        }

        // Create new thinking block (collapsed by default)
        thinkingElement = document.createElement('div');
        thinkingElement.id = thinkingElementId;
        thinkingElement.className = 'thinking-block thinking-active';
        thinkingElement.innerHTML = `
            <div class="thinking-header" onclick="toggleThinkingBlockById(this)">
                <span class="thinking-icon">🧠</span>
                <span class="thinking-header-text">Thinking</span>
                <span class="thinking-expand-icon">▶</span>
            </div>
            <div class="thinking-content" style="display: none;"></div>
        `;

        // Find the last assistant message and insert BEFORE it
        // This ensures thinking block appears before the response
        const messages = container.querySelectorAll('.message:not(.tool-status):not(.thinking-block)');
        const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;

        if (lastMessage && lastMessage.classList.contains('assistant')) {
            // Insert before the last assistant message
            container.insertBefore(thinkingElement, lastMessage);
            console.log('[THINKING DEBUG] Inserted thinking block BEFORE last assistant message');
        } else {
            // No assistant message yet, append to container
            container.appendChild(thinkingElement);
            console.log('[THINKING DEBUG] Appended thinking block to container');
        }
        startThinkingAnimation(thinkingElement);

        if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);

    } else if (status === 'streaming') {
        // Append content to the thinking block
        if (thinkingElement) {
            const contentDiv = thinkingElement.querySelector('.thinking-content');
            if (contentDiv) {
                // Escape HTML and preserve whitespace
                const escapedContent = content
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/\n/g, '<br>');
                contentDiv.innerHTML += escapedContent;
            }
        }

        // Only scroll if the thinking content is expanded
        if (thinkingElement && thinkingElement.classList.contains('expanded') && window.autoScrollEnabled) {
            setTimeout(smoothScrollToBottom, 0);
        }

    } else if (status === 'completed') {
        stopThinkingAnimation();

        if (thinkingElement) {
            // Update header to show "Thought" instead of "Thinking..."
            const textSpan = thinkingElement.querySelector('.thinking-header-text');
            if (textSpan) {
                textSpan.textContent = 'Thought';
            }

            // Mark as completed - remove the ID so it doesn't get confused with new thinking blocks
            thinkingElement.className = 'thinking-block thinking-done';
            thinkingElement.removeAttribute('id');
        }

        if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
    }
}

// Keep for backwards compatibility but use toggleThinkingBlockById
function toggleThinkingBlock() {
    const thinkingElement = document.getElementById('thinking-block-current');
    if (!thinkingElement) return;

    const header = thinkingElement.querySelector('.thinking-header');
    if (header) {
        toggleThinkingBlockById(header);
    }
}

function handleToolStatusUpdate(toolId, toolName, query, status, details) {
    console.log('[TOOL STATUS DEBUG] handleToolStatusUpdate called:', { toolId, toolName, query, status, details });

    const container = document.getElementById('conversation-container');
    if (!container) {
        console.log('[TOOL STATUS DEBUG] Container not found');
        return;
    }

    const toolElementId = `tool-status-${toolId}`;
    let toolElement = document.getElementById(toolElementId);

    if (status === 'starting') {
        console.log('[TOOL STATUS DEBUG] Creating tool status element');
        removeToolStatusesForTool(toolName, toolElementId);
        // Create new tool status element
        if (!toolElement) {
            toolElement = document.createElement('div');
            toolElement.id = toolElementId;
            toolElement.className = 'tool-status tool-status-active';

            // Find the last assistant message and insert BEFORE it
            // This ensures tool status appears before the response that uses the tool
            const messages = container.querySelectorAll('.message:not(.tool-status):not(.thinking-block)');
            const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;

            if (lastMessage && lastMessage.classList.contains('assistant')) {
                // Insert before the last assistant message
                container.insertBefore(toolElement, lastMessage);
                console.log('[TOOL STATUS DEBUG] Inserted tool status BEFORE last assistant message');
            } else {
                // No assistant message yet, append to container
                container.appendChild(toolElement);
                console.log('[TOOL STATUS DEBUG] Appended tool status to container');
            }
        }
        toolElement.dataset.toolName = toolName;

        // Format the "starting" message
        const displayName = getToolDisplayName(toolName);
        const queryPreview = query.length > 50 ? query.substring(0, 50) + '...' : query;
        let html = `
            <div class="tool-status-line">
                <span class="tool-spinner">⏳</span>
                <span class="tool-text">${displayName} for "${queryPreview}"</span>
            </div>
        `;

        if (details && details.trim()) {
            html += `
                <div class="tool-status-line">
                    <span class="tool-spinner">⏳</span>
                    <span class="tool-text tool-details">${details}</span>
                </div>
            `;
        }

        toolElement.innerHTML = html;

        if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
    } else if (status === 'completed') {
        console.log('[TOOL STATUS DEBUG] Updating tool status to completed');
        // Update to "completed" status
        if (toolElement) {
            toolElement.dataset.toolName = toolName;
            const displayName = getToolDisplayName(toolName);
            const queryPreview = query.length > 50 ? query.substring(0, 50) + '...' : query;

            let html = `
                <div class="tool-status-line tool-status-completed">
                    <span class="tool-checkmark">✅</span>
                    <span class="tool-text">${displayName} for "${queryPreview}"</span>
                </div>
            `;

            // Add details line if available
            if (details && details.trim()) {
                html += `
                    <div class="tool-status-line tool-status-completed">
                        <span class="tool-checkmark">✅</span>
                        <span class="tool-text tool-details">${details}</span>
                    </div>
                `;
            }

            toolElement.innerHTML = html;
            toolElement.className = 'tool-status tool-status-done';

            if (window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
        } else {
            console.log('[TOOL STATUS DEBUG] Tool element not found for completed status');
        }
    }
}

function removeToolStatusesForTool(toolName, activeElementId) {
    if (!toolName) return;
    const container = document.getElementById('conversation-container');
    if (!container) return;

    const existingStatuses = container.querySelectorAll('.tool-status');
    existingStatuses.forEach(statusEl => {
        if (
            statusEl.dataset &&
            statusEl.dataset.toolName === toolName &&
            statusEl.id !== activeElementId
        ) {
            statusEl.remove();
        }
    });
}

function clearMessagesKeepToolStatus() {
    const container = document.getElementById('conversation-container');
    if (!container) {
        console.log('[TOOL STATUS DEBUG] Container not found');
        return;
    }

    // Preserve tool status elements only (NOT thinking blocks - they'll be recreated from saved thinking_content)
    const toolStatuses = Array.from(container.querySelectorAll('.tool-status'));
    console.log(`[TOOL STATUS DEBUG] Found ${toolStatuses.length} tool status elements to preserve`);

    // Stop any running thinking animation since we're clearing
    stopThinkingAnimation();

    // Clear all content
    container.innerHTML = '';

    // Re-add tool statuses
    toolStatuses.forEach(toolStatus => {
        console.log('[TOOL STATUS DEBUG] Re-adding tool status:', toolStatus.textContent);
        container.appendChild(toolStatus);
    });
}

function clearMessages() {
    console.log('[TOOL STATUS DEBUG] clearMessages called - clearing everything');
    // Also stop thinking animation if running
    stopThinkingAnimation();
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
