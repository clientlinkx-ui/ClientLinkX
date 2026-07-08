const initSidebar = () => {
    const sidebar = document.getElementById('sidebar');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const collapseBtn = document.getElementById('collapseSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const desktopQuery = window.matchMedia('(min-width: 981px)');

    if (!sidebar) {
        return;
    }

    const closeMobileSidebar = () => {
        sidebar.classList.remove('is-open');
        document.body.classList.remove('sidebar-open');
        mobileMenuBtn?.setAttribute('aria-expanded', 'false');
    };

    const openMobileSidebar = () => {
        sidebar.classList.add('is-open');
        document.body.classList.add('sidebar-open');
        mobileMenuBtn?.setAttribute('aria-expanded', 'true');
    };

    const syncBreakpointState = () => {
        if (desktopQuery.matches) {
            closeMobileSidebar();
        } else {
            sidebar.classList.remove('is-collapsed');
            document.body.classList.remove('sidebar-collapsed');
            collapseBtn?.setAttribute('aria-expanded', 'true');
        }
    };

    mobileMenuBtn?.setAttribute('aria-controls', 'sidebar');
    mobileMenuBtn?.setAttribute('aria-expanded', 'false');
    collapseBtn?.setAttribute('aria-controls', 'sidebar');
    collapseBtn?.setAttribute('aria-expanded', String(!sidebar.classList.contains('is-collapsed')));

    mobileMenuBtn?.addEventListener('click', () => {
        if (sidebar.classList.contains('is-open')) {
            closeMobileSidebar();
        } else {
            openMobileSidebar();
        }
    });

    collapseBtn?.addEventListener('click', () => {
        if (!desktopQuery.matches) {
            closeMobileSidebar();
            return;
        }

        const isCollapsed = sidebar.classList.toggle('is-collapsed');
        document.body.classList.toggle('sidebar-collapsed', isCollapsed);
        collapseBtn.setAttribute('aria-expanded', String(!isCollapsed));
    });

    backdrop?.addEventListener('click', closeMobileSidebar);

    sidebar.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
            if (!desktopQuery.matches) {
                closeMobileSidebar();
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMobileSidebar();
        }
    });

    desktopQuery.addEventListener('change', syncBreakpointState);
    syncBreakpointState();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
} else {
    initSidebar();
}
