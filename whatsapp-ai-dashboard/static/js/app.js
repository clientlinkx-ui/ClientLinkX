const initGlobalSearch = () => {
    const root = document.getElementById('globalSearch');
    const form = document.getElementById('globalSearchForm');
    const input = document.getElementById('globalSearchInput');
    const panel = document.getElementById('globalSearchResults');
    if (!root || !form || !input || !panel) return;

    let timer;
    let requestController;
    let results = [];
    let activeIndex = -1;

    const setOpen = (open) => {
        panel.hidden = !open;
        input.setAttribute('aria-expanded', String(open));
    };

    const showState = (message) => {
        panel.replaceChildren();
        const state = document.createElement('div');
        state.className = 'search-state';
        state.textContent = message;
        panel.appendChild(state);
        setOpen(true);
    };

    const renderResults = (items) => {
        results = items;
        activeIndex = -1;
        panel.replaceChildren();
        if (!items.length) {
            showState('No matching conversations, customers, or AI resources.');
            return;
        }

        items.forEach((item, index) => {
            const link = document.createElement('a');
            link.className = 'search-result';
            link.href = item.url;
            link.setAttribute('role', 'option');
            link.dataset.index = String(index);

            const iconWrap = document.createElement('span');
            iconWrap.className = 'search-result-icon';
            const icon = document.createElement('i');
            icon.className = item.icon;
            iconWrap.appendChild(icon);

            const copy = document.createElement('span');
            copy.className = 'search-result-copy';
            const title = document.createElement('strong');
            title.textContent = item.title;
            const detail = document.createElement('small');
            detail.textContent = item.detail;
            copy.append(title, detail);

            const type = document.createElement('span');
            type.className = 'search-result-type';
            type.textContent = item.type;
            link.append(iconWrap, copy, type);
            panel.appendChild(link);
        });
        setOpen(true);
    };

    const setActive = (index) => {
        const links = [...panel.querySelectorAll('.search-result')];
        if (!links.length) return;
        activeIndex = (index + links.length) % links.length;
        links.forEach((link, linkIndex) => {
            const active = linkIndex === activeIndex;
            link.classList.toggle('is-active', active);
            link.setAttribute('aria-selected', String(active));
        });
        links[activeIndex].scrollIntoView({ block: 'nearest' });
    };

    const runSearch = async () => {
        const query = input.value.trim();
        if (query.length < 2) {
            results = [];
            setOpen(false);
            return;
        }
        requestController?.abort();
        requestController = new AbortController();
        showState('Searching...');
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: requestController.signal });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || 'Search failed.');
            if (input.value.trim() === data.query) renderResults(data.results);
        } catch (error) {
            if (error.name !== 'AbortError') showState('Search is temporarily unavailable.');
        }
    };

    input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(runSearch, 220);
    });
    input.addEventListener('focus', () => {
        if (results.length || input.value.trim().length >= 2) runSearch();
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown') { event.preventDefault(); setActive(activeIndex + 1); }
        if (event.key === 'ArrowUp') { event.preventDefault(); setActive(activeIndex - 1); }
        if (event.key === 'Escape') { setOpen(false); input.blur(); }
    });
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const target = panel.querySelector('.search-result.is-active') || panel.querySelector('.search-result');
        if (target) window.location.assign(target.href);
        else runSearch();
    });
    document.addEventListener('click', (event) => {
        if (!root.contains(event.target)) setOpen(false);
    });
    document.addEventListener('keydown', (event) => {
        const tag = document.activeElement?.tagName;
        if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
            event.preventDefault();
            input.focus();
        }
    });
};

const initTopbarInbox = () => {
    const actions = [...document.querySelectorAll('.nav-action[data-inbox]')];
    if (!actions.length) return;

    const closePanels = (except) => {
        actions.forEach((action) => {
            if (action === except) return;
            action.querySelector('.inbox-panel').hidden = true;
            action.querySelector('.inbox-trigger').setAttribute('aria-expanded', 'false');
        });
    };

    const updateBadge = (action, unread) => {
        const badge = action.querySelector('[data-badge]');
        badge.textContent = String(unread);
        badge.hidden = unread === 0;
    };

    const renderState = (action, message) => {
        const list = action.querySelector('[data-list]');
        const state = document.createElement('div');
        state.className = 'inbox-state';
        state.textContent = message;
        list.replaceChildren(state);
    };

    const createItem = (action, kind, item) => {
        const link = document.createElement('a');
        link.className = `inbox-item${item.is_read ? '' : ' unread'}`;
        link.href = item.url;

        const icon = document.createElement('span');
        icon.className = 'inbox-item-icon';
        if (kind === 'messages') {
            icon.textContent = item.initials;
        } else {
            const symbol = document.createElement('i');
            symbol.className = item.icon;
            icon.appendChild(symbol);
        }

        const copy = document.createElement('span');
        copy.className = 'inbox-item-copy';
        const title = document.createElement('strong');
        title.textContent = kind === 'messages' ? item.sender : item.title;
        const detail = document.createElement('small');
        detail.textContent = kind === 'messages' ? item.preview : item.body;
        copy.append(title, detail);

        const time = document.createElement('time');
        time.textContent = item.time;
        link.append(icon, copy, time);

        link.addEventListener('click', async (event) => {
            event.preventDefault();
            if (!item.is_read) {
                await fetch(`/api/topbar/${kind}/${item.id}`, { method: 'PATCH' }).catch(() => null);
            }
            window.location.assign(item.url);
        });
        return link;
    };

    const loadInbox = async (action) => {
        const kind = action.dataset.inbox;
        renderState(action, `Loading ${kind}...`);
        try {
            const response = await fetch(`/api/topbar/${kind}`);
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || 'Could not load inbox.');
            updateBadge(action, data.unread);
            const list = action.querySelector('[data-list]');
            if (!data.items.length) {
                renderState(action, kind === 'messages' ? 'No recent messages.' : 'No notifications.');
                return;
            }
            list.replaceChildren(...data.items.map((item) => createItem(action, kind, item)));
        } catch (error) {
            renderState(action, error.message);
        }
    };

    actions.forEach((action) => {
        const trigger = action.querySelector('.inbox-trigger');
        const panel = action.querySelector('.inbox-panel');
        const readAll = action.querySelector('.inbox-read-all');
        trigger.addEventListener('click', async () => {
            const willOpen = panel.hidden;
            closePanels(action);
            panel.hidden = !willOpen;
            trigger.setAttribute('aria-expanded', String(willOpen));
            if (willOpen) await loadInbox(action);
        });
        readAll.addEventListener('click', async () => {
            const kind = action.dataset.inbox;
            readAll.disabled = true;
            await fetch(`/api/topbar/${kind}/read-all`, { method: 'POST' }).catch(() => null);
            await loadInbox(action);
            readAll.disabled = false;
        });
        loadInbox(action);
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.nav-action')) closePanels();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closePanels();
    });
};

const initAccountMenu = () => {
    const root = document.getElementById('accountMenu');
    const button = document.getElementById('accountMenuButton');
    const menu = document.getElementById('accountDropdown');
    if (!root || !button || !menu) return;

    const setOpen = (open) => {
        menu.hidden = !open;
        button.setAttribute('aria-expanded', String(open));
    };

    button.addEventListener('click', () => setOpen(menu.hidden));
    button.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            setOpen(true);
            menu.querySelector('a')?.focus();
        }
    });
    document.addEventListener('click', (event) => {
        if (!root.contains(event.target)) setOpen(false);
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') setOpen(false);
    });
};

const initPersonalization = () => {
    const form = document.getElementById('personalizationForm');
    const status = document.getElementById('personalizationStatus');
    if (!form || !status) return;

    const setStatus = (message, tone = 'neutral') => {
        status.textContent = message;
        status.classList.toggle('good', tone === 'good');
        status.classList.toggle('warning', tone === 'warning');
        status.classList.toggle('neutral-badge', tone === 'neutral');
    };

    const applyPreferences = (preferences) => {
        document.body.classList.remove(
            'theme-auto', 'theme-light', 'theme-dark',
            'density-comfortable', 'density-compact',
            'accent-teal', 'accent-blue', 'accent-green', 'accent-violet',
            'sidebar-collapsed',
        );
        document.body.classList.add(
            `theme-${preferences.console_theme}`,
            `density-${preferences.console_density}`,
            `accent-${preferences.accent_color}`,
        );
        const sidebar = document.getElementById('sidebar');
        const collapseBtn = document.getElementById('collapseSidebar');
        const collapsed = preferences.default_sidebar === 'collapsed';
        document.body.classList.toggle('sidebar-collapsed', collapsed);
        sidebar?.classList.toggle('is-collapsed', collapsed);
        collapseBtn?.setAttribute('aria-expanded', String(!collapsed));
    };

    form.addEventListener('change', () => {
        applyPreferences(Object.fromEntries(new FormData(form).entries()));
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        setStatus('Saving...', 'warning');
        try {
            const response = await fetch('/api/account/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.fromEntries(new FormData(form).entries())),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || 'Could not save preferences.');
            applyPreferences(data.preferences);
            setStatus('Preferences saved', 'good');
        } catch (error) {
            setStatus(error.message, 'warning');
        } finally {
            button.disabled = false;
        }
    });
};

const initApp = () => {
    initGlobalSearch();
    initTopbarInbox();
    initAccountMenu();
    initPersonalization();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
