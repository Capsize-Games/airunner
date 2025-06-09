// conversation_theme.js - Dynamic theme switching for conversation widget
function setTheme(themeName) {
    document.querySelectorAll('link[data-theme-css]').forEach(link => link.remove());
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
// Optionally, set initial theme on load if available
if (window.currentTheme) {
    setTheme(window.currentTheme);
}

document.addEventListener('DOMContentLoaded', function () {
    let theme = 'dark';
    const themeVars = document.getElementById('theme-vars');
    if (themeVars && themeVars.href) {
        const match = themeVars.href.match(/variables-([a-zA-Z0-9_-]+)\.css/);
        if (match) theme = match[1];
    }
    setTheme(theme);
    console.log('Conversation widget loaded, theme:', theme);
});
