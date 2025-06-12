// home.js - Placeholder for AI Runner Home interactivity
function setTheme(themeName) {
    // Remove existing theme/variable CSS links
    document.querySelectorAll('link[data-theme-css]').forEach(link => link.remove());
    // Add variables CSS
    const variablesHref = `static/css/variables-${themeName}.css`;
    const themeHref = `static/css/theme-${themeName}.css`;
    [variablesHref, themeHref].forEach(href => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.setAttribute('data-theme-css', '1');
        document.head.appendChild(link);
    });
}

window.setTheme = setTheme;

document.addEventListener('DOMContentLoaded', function () {
    // Prefer theme from meta tag if available
    let theme = document.querySelector('meta[name="airunner-theme"]')?.content || window.currentTheme || 'light';
    setTheme(theme);
    console.log('AI Runner Home loaded, theme:', theme);
});
