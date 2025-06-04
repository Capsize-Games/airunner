// conversation.js: JavaScript for conversation widget with MathJax integration

console.log('[ConversationWidget] conversation.js loaded');
if (typeof QWebChannel === 'undefined') {
    console.error('[ConversationWidget] QWebChannel is NOT defined!');
} else {
    console.log('[ConversationWidget] QWebChannel is defined.');
}
if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
    console.error('[ConversationWidget] qt.webChannelTransport is NOT available!');
} else {
    console.log('[ConversationWidget] qt.webChannelTransport is available.');
}

let chatBridge = null;
window.isChatReady = false;
window.chatReady = new Promise((resolve) => {
    window.chatReadyResolve = resolve;
});

function initializeChatView() {
    console.log('[ConversationWidget] DOMContentLoaded');
    const container = document.getElementById('conversation-container');
    if (container) {
        console.log('[ConversationWidget] Container found:', container.offsetHeight, 'height,', container.scrollHeight, 'scrollHeight');
    } else {
        console.error('[ConversationWidget] No container found on DOMContentLoaded!');
        return;
    }

    new QWebChannel(qt.webChannelTransport, function (channel) {
        chatBridge = channel.objects.chatBridge;
        window.chatBridge = chatBridge;

        if (!chatBridge) {
            console.error('[ConversationWidget] chatBridge object not found in QWebChannel.objects');
            return;
        }

        chatBridge.appendMessage.connect(appendMessage);
        chatBridge.clearMessages.connect(clearMessages);
        chatBridge.setMessages.connect(function (msgs) {
            clearMessages();
            const renderPromises = [];
            for (let i = 0; i < msgs.length; ++i) {
                renderPromises.push(appendMessage(msgs[i], false));
            }
            Promise.all(renderPromises).then(() => {
                console.log('[ConversationWidget] setMessages: rendered', msgs.length, 'messages, attempting scroll...');
                setTimeout(smoothScrollToBottom, 0);
                setTimeout(smoothScrollToBottom, 100);
                setTimeout(smoothScrollToBottom, 300);
            });
        });

        window.isChatReady = true;
        console.log('[ConversationWidget] QWebChannel initialized, chatBridge available:', !!window.chatBridge);
        if (window.chatReadyResolve) {
            window.chatReadyResolve();
            delete window.chatReadyResolve;
        }
        console.debug('[ConversationWidget] QWebChannel ready');

        setTimeout(smoothScrollToBottom, 50);
    });

    // MutationObserver for streaming updates and dynamic content changes
    if (container) {
        const observer = new MutationObserver((mutations) => {
            let needsScroll = false;
            let needsTypeset = false;
            for (const mutation of mutations) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    needsScroll = true;
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            needsTypeset = true;
                        }
                    });
                } else if (mutation.type === 'characterData') {
                    needsTypeset = true;
                }
            }
            if (needsScroll) {
                setTimeout(smoothScrollToBottom, 0);
            }
            if (needsTypeset && window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
                clearTimeout(window.mathJaxTypesetTimeout);
                window.mathJaxTypesetTimeout = setTimeout(() => {
                    console.debug('[ConversationWidget] MutationObserver: Triggering MathJax.typesetPromise()');
                    window.MathJax.typesetPromise([container]).catch(err => console.error('MathJax typesetting error:', err));
                }, 50);
            }
        });
        observer.observe(container, { childList: true, subtree: true, characterData: true });
    }
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
    contentDiv.innerHTML = msg.content;
    messageDiv.appendChild(contentDiv);

    if (msg.timestamp) {
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        try {
            // Format timestamp for better readability
            const date = new Date(msg.timestamp);
            timestampDiv.textContent = date.toLocaleString();
        } catch (e) {
            timestampDiv.textContent = msg.timestamp; // Fallback to raw timestamp
        }
        messageDiv.appendChild(timestampDiv);
    }
    return messageDiv;
}

async function appendMessage(msg, scroll = true) {
    const container = document.getElementById('conversation-container');
    if (!container) {
        console.error('[ConversationWidget] appendMessage: conversation-container not found');
        return;
    }

    const messageElement = createMessageElement(msg);
    container.appendChild(messageElement);
    console.debug('[ConversationWidget] appendMessage: added message', msg);

    // Typeset the new message with MathJax
    if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
        try {
            await window.MathJax.typesetPromise([messageElement]);
            console.debug('[ConversationWidget] MathJax processed new message.');
        } catch (err) {
            console.error('MathJax typesetting error on appendMessage:', err);
        }
    } else {
        // console.warn('[ConversationWidget] MathJax not available or typesetPromise is not a function.');
    }

    if (scroll) {
        setTimeout(smoothScrollToBottom, 0);
    }
}

function clearMessages() {
    const container = document.getElementById('conversation-container');
    if (!container) {
        console.error('[ConversationWidget] clearMessages: conversation-container not found');
        return;
    }
    container.innerHTML = '';
    console.debug('[ConversationWidget] clearMessages: cleared all messages');
}

function smoothScrollToBottom() {
    const container = document.getElementById('conversation-container');
    if (container) {
        const contentHeight = container.scrollHeight;

        if (window.isChatReady && window.chatBridge && typeof window.chatBridge.update_content_height === 'function') {
            window.chatBridge.update_content_height(contentHeight);
        } else if (!window.isChatReady) {
            console.debug('[ConversationWidget] QWebChannel not ready yet (isChatReady:', window.isChatReady, '), retrying scroll in 100ms');
            setTimeout(smoothScrollToBottom, 100);
        } else if (!window.chatBridge) {
            console.warn('[ConversationWidget] chatBridge object not available (isChatReady:', window.isChatReady, ')');
            setTimeout(smoothScrollToBottom, 100);
        } else {
            console.warn('[ConversationWidget] smoothScrollToBottom: chatBridge available but could not proceed.');
        }
    } else {
        console.warn('[ConversationWidget] smoothScrollToBottom - No container found');
    }
}

// Initialize when the DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatView);
} else {
    initializeChatView();
}
