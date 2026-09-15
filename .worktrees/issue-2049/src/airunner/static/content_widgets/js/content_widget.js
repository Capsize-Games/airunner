// content_widget.js
// Handles dynamic height adjustment for the content widget in QWebEngineView

(function () {
    'use strict';

    function adjustContentHeight() {
        var height = (document.body && document.body.scrollHeight) ? document.body.scrollHeight : 100;
        window.scrollTo(0, 0);
        return height;
    }

    // Expose the function globally
    window.adjustContentHeight = adjustContentHeight;

    // Also ensure it's available immediately
    if (typeof window.adjustContentHeight === 'undefined') {
        window.adjustContentHeight = adjustContentHeight;
    }
})();
