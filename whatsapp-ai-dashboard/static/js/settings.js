const initSettingsNavigation = () => {
    const navLinks = [...document.querySelectorAll('.settings-nav a')];
    const root = document.querySelector('.settings-page');
    const sections = navLinks
        .map((link) => document.querySelector(link.getAttribute('href')))
        .filter(Boolean);

    if (!root || !navLinks.length || !sections.length || !window.PingPilot?.initOnce(root, 'settings-nav')) {
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

    window.PingPilotSettingsScroll?.abort();
    window.PingPilotSettingsScroll = new AbortController();
    window.addEventListener('scroll', () => {
        const current = sections
            .filter((section) => section.getBoundingClientRect().top < 150)
            .at(-1);

        if (current) {
            setActive(current.id);
        }
    }, { passive: true, signal: window.PingPilotSettingsScroll.signal });
};

window.PingPilot?.ready ? PingPilot.ready(initSettingsNavigation) : document.addEventListener('DOMContentLoaded', initSettingsNavigation);
document.addEventListener('pingpilot:page-ready', initSettingsNavigation);
document.addEventListener('pingpilot:before-page-swap', () => {
    window.PingPilotSettingsScroll?.abort();
});
