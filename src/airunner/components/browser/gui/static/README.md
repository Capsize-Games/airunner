# Browser Widget API

The Browser Widget provides a generic, reusable system for creating browser-based applications that can communicate with the Python backend. This system is framework-agnostic and can be used for any type of interactive web application.

## Architecture

### Components

1. **BrowserAPI (`api.js`)** - Generic JavaScript API for browser-widget communication
2. **BrowserWidget (`browser_widget.py`)** - Python widget that hosts the browser and handles communication
3. **BrowserWidgetHandler** - Generic command handler for processing JavaScript commands
4. **Application-specific code** - Your custom JavaScript and Python logic

### Communication Flow

```
JavaScript App ↔ BrowserAPI ↔ WebChannel ↔ BrowserWidgetHandler ↔ Python Backend
```

## Getting Started

### 1. Create Your HTML Template

Create an HTML file (can be Jinja2 template) in your application directory:

```html
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>
</head>
<body>
    <h1>My Application</h1>
    <button id="myButton">Click Me</button>
    
    <!-- Load the generic API first -->
    <script src="{{ static_base_path }}/js/api.js"></script>
    <script>
        // Wait for API to load, then load your app script
        function waitForBrowserAPI() {
            if (window.browserAPI) {
                const appScript = document.createElement('script');
                appScript.src = '{{ static_base_path }}/myapp/js/app.js';
                document.head.appendChild(appScript);
            } else {
                setTimeout(waitForBrowserAPI, 50);
            }
        }
        waitForBrowserAPI();
    </script>
</body>
</html>
```

### 2. Create Your JavaScript Application

Create your application logic that uses the BrowserAPI:

```javascript
// myapp/js/app.js
class MyApp {
    constructor(browserAPI) {
        this.api = browserAPI;
        this.isReady = false;
    }

    async initialize() {
        await this.api.ready();
        this.isReady = true;
        
        // Listen for responses
        this.api.on('response', this._handleResponse.bind(this));
    }

    // Send commands to Python backend
    doSomething(data) {
        return this.api.sendCommand('my_action', data);
    }

    _handleResponse(response) {
        console.log('Received response:', response);
    }
}

// Initialize when DOM is ready
function initializeApp() {
    if (window.browserAPI) {
        const app = new MyApp(window.browserAPI);
        app.initialize();
        
        // Set up UI event handlers
        document.getElementById('myButton').addEventListener('click', () => {
            app.doSomething({ message: 'Hello from browser!' });
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
```

### 3. Handle Commands in Python

Listen for the `WIDGET_COMMAND_SIGNAL` in your Python code:

```python
from airunner.enums import SignalCode

class MyAppHandler:
    def __init__(self):
        # Listen for widget commands
        self.register_signal_handler(SignalCode.WIDGET_COMMAND_SIGNAL, self.handle_widget_command)
    
    def handle_widget_command(self, data):
        command = data.get('command')
        command_data = data.get('data', {})
        
        if command == 'my_action':
            # Handle your custom command
            print(f"Received my_action: {command_data}")
            # Process the command and optionally send response back
```

## API Reference

### BrowserAPI (JavaScript)

#### Methods

- `sendCommand(command, data)` - Send a command to the Python backend
- `ready()` - Returns a Promise that resolves when the API is ready
- `isReady()` - Returns boolean indicating if API is ready
- `on(eventType, callback)` - Register event listener
- `off(eventType, callback)` - Remove event listener

#### Events

- `'api-ready'` - Fired when the API is initialized
- `'response'` - Fired for all responses from Python
- `'response-{type}'` - Fired for specific response types

### BrowserWidget (Python)

#### Signals

- `SignalCode.WIDGET_COMMAND_SIGNAL` - Emitted when JavaScript sends a command

#### Response Method

Use `browser_widget._send_response(response_type, message)` to send responses back to JavaScript.

## Best Practices

1. Always wait for `browserAPI` to be available before using it
2. Use specific command names to avoid conflicts
3. Handle errors gracefully in both JavaScript and Python
4. Use the event system for loose coupling between components
5. Keep the generic API clean - put application-specific logic in your own wrapper classes
