/**
 * Generic Browser Widget Communication API
 * Handles all communication between JavaScript and the browser widget
 * This API is framework-agnostic and can be used for any type of application
 */
class BrowserAPI {
    constructor() {
        this.handler = null;
        this.isInitialized = false;
        this.eventCallbacks = new Map();
        this.pendingCommands = [];

        this.initialize();
    }

    /**
     * Initialize WebChannel communication
     */
    initialize() {
        console.log('BrowserAPI: Initializing...');

        // Listen for WebChannel ready event
        window.addEventListener('qwebchannelready', () => {
            console.log('BrowserAPI: QWebChannel script loaded, initializing...');
            setTimeout(() => this._initializeWebChannel(), 100);
        });

        // Try to initialize WebChannel immediately in case it's already available
        setTimeout(() => this._initializeWebChannel(), 100);

        // Also try again after a longer delay
        setTimeout(() => this._initializeWebChannel(), 1000);

        // Listen for messages from the browser widget
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'widget_response') {
                this._handleResponse(event.data);
            }
        });
    }

    /**
     * Internal method to initialize WebChannel
     */
    _initializeWebChannel() {
        if (typeof qt !== 'undefined' && qt.webChannelTransport && typeof QWebChannel !== 'undefined') {
            new QWebChannel(qt.webChannelTransport, (channel) => {
                // Look for any available handler (gameHandler, widgetHandler, etc.)
                this.handler = channel.objects.gameHandler || channel.objects.widgetHandler || channel.objects.handler;
                this.isInitialized = true;
                console.log('BrowserAPI: WebChannel initialized, handler available');

                // Process any pending commands
                this._processPendingCommands();

                // Notify listeners that API is ready
                this._triggerEvent('api-ready');
            });
        } else {
            console.log('BrowserAPI: WebChannel not available, using fallback communication');
            this.isInitialized = true;

            // Process pending commands with fallback
            this._processPendingCommands();

            // Notify listeners that API is ready (with fallback)
            this._triggerEvent('api-ready');
        }
    }

    /**
     * Send a command to the browser widget
     * @param {string} command - The command to send
     * @param {Object} data - Additional data for the command
     * @returns {Promise} Promise that resolves when command is sent
     */
    sendCommand(command, data = {}) {
        return new Promise((resolve, reject) => {
            const message = {
                type: 'widget_command',
                command: command,
                data: data,
                timestamp: Date.now(),
                id: this._generateCommandId()
            };

            console.log('BrowserAPI: Sending command:', command);

            if (!this.isInitialized) {
                // Queue the command if API is not ready
                this.pendingCommands.push({ message, resolve, reject });
                console.log('BrowserAPI: Command queued (API not ready)');
                return;
            }

            this._executeCommand(message, resolve, reject);
        });
    }

    /**
     * Execute a command immediately
     */
    _executeCommand(message, resolve, reject) {
        let commandSent = false;

        // Try WebChannel first
        if (this.handler) {
            try {
                // Try different method names that might be available
                if (this.handler.handleGameCommand) {
                    this.handler.handleGameCommand(JSON.stringify(message));
                } else if (this.handler.handleCommand) {
                    this.handler.handleCommand(JSON.stringify(message));
                } else if (this.handler.handleWidgetCommand) {
                    this.handler.handleWidgetCommand(JSON.stringify(message));
                }
                console.log('BrowserAPI: Command sent via WebChannel');
                commandSent = true;
                resolve({ success: true, method: 'webchannel' });
            } catch (e) {
                console.warn('BrowserAPI: WebChannel command failed:', e);
            }
        }

        // Fallback to postMessage if WebChannel failed
        if (!commandSent) {
            try {
                window.parent.postMessage(message, '*');
                console.log('BrowserAPI: Command sent via postMessage');
                commandSent = true;
                resolve({ success: true, method: 'postmessage' });
            } catch (e) {
                console.warn('BrowserAPI: Could not send message to parent:', e);
            }
        }

        // Final fallback - just log
        if (!commandSent) {
            console.log('BrowserAPI: Command (fallback logging):', message.command, message.data);
            resolve({ success: true, method: 'console' });
        }
    }

    /**
     * Process pending commands
     */
    _processPendingCommands() {
        console.log(`BrowserAPI: Processing ${this.pendingCommands.length} pending commands`);

        while (this.pendingCommands.length > 0) {
            const { message, resolve, reject } = this.pendingCommands.shift();
            this._executeCommand(message, resolve, reject);
        }
    }

    /**
     * Handle responses from the browser widget
     */
    _handleResponse(response) {
        console.log('BrowserAPI: Received response:', response);
        this._triggerEvent('response', response);

        // Handle specific response types
        if (response.response_type) {
            this._triggerEvent(`response-${response.response_type}`, response);
        }

        // Handle specific commands
        if (response.command) {
            this._triggerEvent(`command-${response.command}`, response);
        }
    }

    /**
     * Register event listeners
     * @param {string} eventType - The event type to listen for
     * @param {Function} callback - The callback function
     */
    on(eventType, callback) {
        if (!this.eventCallbacks.has(eventType)) {
            this.eventCallbacks.set(eventType, []);
        }
        this.eventCallbacks.get(eventType).push(callback);
    }

    /**
     * Remove event listeners
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback function to remove
     */
    off(eventType, callback) {
        if (this.eventCallbacks.has(eventType)) {
            const callbacks = this.eventCallbacks.get(eventType);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Trigger events to registered listeners
     */
    _triggerEvent(eventType, data = null) {
        if (this.eventCallbacks.has(eventType)) {
            this.eventCallbacks.get(eventType).forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error(`BrowserAPI: Error in event callback for ${eventType}:`, e);
                }
            });
        }
    }

    /**
     * Generate unique command ID
     */
    _generateCommandId() {
        return `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Utility method to check if API is ready
     */
    isReady() {
        return this.isInitialized;
    }

    /**
     * Utility method to wait for API to be ready
     */
    ready() {
        return new Promise((resolve) => {
            if (this.isInitialized) {
                resolve();
            } else {
                this.on('api-ready', resolve);
            }
        });
    }
}

// Create global API instance
window.browserAPI = new BrowserAPI();
console.log('BrowserAPI: Global instance created and available at window.browserAPI');

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BrowserAPI;
}
