# content_widgets/README.md

This directory contains static assets (HTML, CSS, JS) for content widgets used in the AI Runner application.

- `html/`: Jinja2 HTML templates for rendering content widgets.
- `css/`: Stylesheets for content widgets (to be separated from HTML as needed).
- `js/`: JavaScript files for dynamic behavior in content widgets (e.g., height adjustment for QWebEngineView).

## Usage

- Content widgets in Python (e.g., `MarkdownWidget`) load and render these templates using Jinja2.
- JavaScript and CSS are referenced in the HTML templates and executed in the embedded web view.

## Example

- `content_widget.jinja2.html` is the main template for rendering markdown/HTML content with MathJax and syntax highlighting.
- `content_widget.js` provides a function for dynamic height adjustment, called from Python via QWebEngineView's `runJavaScript`.

## Conventions

- Keep logic and presentation separated: no inline JS or CSS in Python; use static files.
- Update this README when adding new static assets or templates.

## Jinja2 Template Integration (2025-05-31)

- Each message in the ConversationWidget is rendered using a Jinja2 template from `html/` based on its content type (plain, latex, mixed, etc).
- The backend determines the correct template and passes its path as `widget_template` in each message dict.
- The main conversation template includes the correct widget template for each message:

```jinja2
{% for msg in messages %}
  {% include msg.widget_template %}
{% endfor %}
```

- To add a new content type, add a new template to `html/` and update the backend mapping.
