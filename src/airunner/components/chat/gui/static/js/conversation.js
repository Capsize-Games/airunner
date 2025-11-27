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
            const messages = container.querySelectorAll('.message:not(.tool-status)');
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
    const messageElement = createMessageElement(msg);
    container.appendChild(messageElement);
    if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
        try { await window.MathJax.typesetPromise([messageElement]); } catch { }
    }
    if (scroll && window.autoScrollEnabled) setTimeout(smoothScrollToBottom, 0);
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
            container.appendChild(toolElement);
            console.log('[TOOL STATUS DEBUG] Appended new tool status element to container');
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

    // Preserve tool status elements
    const toolStatuses = Array.from(container.querySelectorAll('.tool-status'));
    console.log(`[TOOL STATUS DEBUG] Found ${toolStatuses.length} tool status elements to preserve`);

    // Clear all content
    container.innerHTML = '';

    // Re-add tool statuses at the beginning
    toolStatuses.forEach(toolStatus => {
        console.log('[TOOL STATUS DEBUG] Re-adding tool status:', toolStatus.textContent);
        container.appendChild(toolStatus);
    });
}

function clearMessages() {
    console.log('[TOOL STATUS DEBUG] clearMessages called - clearing everything');
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
