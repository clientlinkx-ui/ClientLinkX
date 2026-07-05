const initSettingsNavigation = () => {
    const navLinks = [...document.querySelectorAll('.settings-nav a')];
    const sections = navLinks
        .map((link) => document.querySelector(link.getAttribute('href')))
        .filter(Boolean);

    if (!navLinks.length || !sections.length) {
        return;
    }

    const setActive = (id) => {
        navLinks.forEach((link) => {
            link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
        });
    };

    navLinks.forEach((link) => {
        link.addEventListener('click', () => {
            const targetId = link.getAttribute('href').slice(1);
            setActive(targetId);
        });
    });

    window.addEventListener('scroll', () => {
        const current = sections
            .filter((section) => section.getBoundingClientRect().top < 150)
            .at(-1);

        if (current) {
            setActive(current.id);
        }
    }, { passive: true });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSettingsNavigation);
} else {
    initSettingsNavigation();
}
