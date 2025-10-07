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
        if (needsScroll) setTimeout(smoothScrollToBottom, 0);
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
    // Attach context menu handler to both user and assistant messages
    let headerDiv = messageDiv.querySelector('.header');
    if (!headerDiv) {
        headerDiv = document.createElement('div');
        headerDiv.className = 'header';
        headerDiv.appendChild(senderDiv);
        messageDiv.insertBefore(headerDiv, contentDiv);
    }

    messageDiv.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        // Remove any existing custom menu
        const existing = document.getElementById('chat-context-menu');
        if (existing) existing.remove();

        const menu = document.createElement('div');
        menu.id = 'chat-context-menu';
        menu.className = 'chat-context-menu';
        menu.style.position = 'fixed';
        menu.style.zIndex = 99999;
        menu.style.left = e.clientX + 'px';
        menu.style.top = e.clientY + 'px';
        menu.style.background = 'var(--background, #222)';
        menu.style.border = '1px solid rgba(255,255,255,0.08)';
        menu.style.padding = '4px';
        menu.style.borderRadius = '6px';
        menu.style.minWidth = '140px';

        function addItem(label, onClick) {
            const item = document.createElement('div');
            item.className = 'chat-context-menu-item';
            item.style.padding = '6px 10px';
            item.style.cursor = 'pointer';
            item.style.color = 'var(--text, #eee)';
            item.textContent = label;
            item.addEventListener('click', function () {
                onClick();
                menu.remove();
            });
            item.addEventListener('mouseover', () => item.style.background = 'rgba(255,255,255,0.03)');
            item.addEventListener('mouseout', () => item.style.background = 'transparent');
            menu.appendChild(item);
        }

        // Copy is available for all messages
        addItem('Copy', function () {
            if (window.chatBridge && typeof window.chatBridge.copyMessage === 'function') {
                window.chatBridge.copyMessage(msg.id);
            } else {
                // Fallback: copy visible text
                const text = contentDiv ? contentDiv.innerText : (msg.content || '');
                if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).catch(() => { });
            }
        });

        if (!msg.is_bot) {
            addItem('Delete', function () {
                if (window.chatBridge && typeof window.chatBridge.deleteMessage === 'function') {
                    window.chatBridge.deleteMessage(msg.id);
                }
            });
            // divider
            const hr = document.createElement('div');
            hr.style.height = '1px';
            hr.style.background = 'rgba(255,255,255,0.04)';
            hr.style.margin = '6px 0';
            menu.appendChild(hr);
            addItem('New chat', function () {
                if (window.chatBridge && typeof window.chatBridge.newChat === 'function') {
                    window.chatBridge.newChat();
                }
            });
        } else {
            // assistant messages: only Copy, divider, New chat
            const hr = document.createElement('div');
            hr.style.height = '1px';
            hr.style.background = 'rgba(255,255,255,0.04)';
            hr.style.margin = '6px 0';
            menu.appendChild(hr);
            addItem('New chat', function () {
                if (window.chatBridge && typeof window.chatBridge.newChat === 'function') {
                    window.chatBridge.newChat();
                }
            });
        }

        document.body.appendChild(menu);

        function onDocClick(ev) {
            if (!menu.contains(ev.target)) menu.remove();
        }

        setTimeout(() => document.addEventListener('click', onDocClick), 0);
    });
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
