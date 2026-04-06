function initTheme() {
    const savedTheme = localStorage.getItem('tuneflow_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
    } else if (savedTheme === 'light') {
        document.body.classList.remove('dark');
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) document.body.classList.add('dark');
        else document.body.classList.remove('dark');
    }
    const savedAccent = localStorage.getItem('tuneflow_accent');
    if (savedAccent) document.body.setAttribute('data-accent', savedAccent);
    else document.body.setAttribute('data-accent', 'purple');
}
function initColorPicker() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.body.classList.contains('dark');
            if (isDark) {
                document.body.classList.remove('dark');
                localStorage.setItem('tuneflow_theme', 'light');
            } else {
                document.body.classList.add('dark');
                localStorage.setItem('tuneflow_theme', 'dark');
            }
        });
    }
    const colorBtns = document.querySelectorAll('.color-btn');
    colorBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const color = btn.dataset.color;
            if (color) {
                document.body.setAttribute('data-accent', color);
                localStorage.setItem('tuneflow_accent', color);
                colorBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            }
        });
    });
}