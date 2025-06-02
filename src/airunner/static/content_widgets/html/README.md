# Content Widgets HTML Templates

This directory previously contained multiple Jinja2 templates for different content types (LaTeX, mixed, plain text, etc.).

## Current State (as of June 2025)

- **conversation.jinja2.html**: The only template now used for conversation display. It supports all content types (plain text, markdown, LaTeX, mixed) via MathJax and external CSS/JS. All message rendering is handled by this single, robust template.
- **[Removed]** latex_widget.jinja2.html, mixed_content_widget.jinja2.html, plain_text_widget.jinja2.html, content_widget.jinja2.html: These are now obsolete and have been removed as part of the conversation system refactor.

## Rationale
- The conversation system is now DRY, robust, and easy to maintain.
- MathJax is used for all mathematical and code rendering.
- All CSS and JS are external and modular.

See the main project README for more details.
