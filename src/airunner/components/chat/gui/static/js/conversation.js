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
        chatBridge.setMessages.connect(function (msgs) {
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
    // No DOMPurify: allow trusted HTML from backend (assume backend sanitizes)
    // This enables MathJax, code, and markdown rendering as intended.
    return html;
}

function createMessageElement(msg) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + (msg.is_bot ? 'assistant' : 'user');
    messageDiv.setAttribute('data-message-id', msg.id || Date.now());
    const senderDiv = document.createElement('div');
    senderDiv.className = 'sender';
    senderDiv.textContent = msg.name || msg.sender || (msg.is_bot ? 'Assistant' : 'User');
    messageDiv.appendChild(senderDiv);
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.innerHTML = sanitizeContent(msg.content);
    messageDiv.appendChild(contentDiv);
    if (!msg.is_bot) {
        // Create actions container if not present
        let headerDiv = messageDiv.querySelector('.header');
        if (!headerDiv) {
            headerDiv = document.createElement('div');
            headerDiv.className = 'header';
            headerDiv.appendChild(senderDiv);
            messageDiv.insertBefore(headerDiv, contentDiv);
        }
        let actionsDiv = document.createElement('div');
        actionsDiv.className = 'actions';
        // Create delete button with inline SVG
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
    }
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

function clearMessages() {
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
