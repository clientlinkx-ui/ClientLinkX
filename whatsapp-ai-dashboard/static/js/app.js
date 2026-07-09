const PingPilot = window.PingPilot || {};

PingPilot.initOnce = (element, key) => {
    if (!element) return false;
    const attribute = `data-initialized-${key}`;
    if (element.hasAttribute(attribute)) return false;
    element.setAttribute(attribute, 'true');
    return true;
};

PingPilot.ready = (callback) => {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
        callback();
    }
};

PingPilot.emitPageReady = () => {
    document.dispatchEvent(new CustomEvent('pingpilot:page-ready'));
};

PingPilot.emitBeforePageSwap = () => {
    document.dispatchEvent(new CustomEvent('pingpilot:before-page-swap'));
};

window.PingPilot = PingPilot;

const initGlobalSearch = () => {
    const root = document.getElementById('globalSearch');
    const form = document.getElementById('globalSearchForm');
    const input = document.getElementById('globalSearchInput');
    const panel = document.getElementById('globalSearchResults');
    if (!root || !form || !input || !panel || !PingPilot.initOnce(root, 'global-search')) return;

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
        if (target) window.PingPilotNavigation?.go(target.href) || window.location.assign(target.href);
        else runSearch();
    });
    document.addEventListener('click', (event) => {
        if (!root.contains(event.target)) setOpen(false);
    });
    if (!document.documentElement.hasAttribute('data-search-shortcut-ready')) {
        document.documentElement.setAttribute('data-search-shortcut-ready', 'true');
        document.addEventListener('keydown', (event) => {
            const tag = document.activeElement?.tagName;
            if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
                event.preventDefault();
                document.getElementById('globalSearchInput')?.focus();
            }
        });
    }
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
            window.PingPilotNavigation?.go(item.url) || window.location.assign(item.url);
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
        if (!PingPilot.initOnce(action, 'inbox')) return;
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

    if (!document.documentElement.hasAttribute('data-inbox-dismiss-ready')) {
        document.documentElement.setAttribute('data-inbox-dismiss-ready', 'true');
        document.addEventListener('click', (event) => {
            if (!event.target.closest('.nav-action')) {
                document.querySelectorAll('.nav-action[data-inbox]').forEach((action) => {
                    action.querySelector('.inbox-panel').hidden = true;
                    action.querySelector('.inbox-trigger').setAttribute('aria-expanded', 'false');
                });
            }
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                document.querySelectorAll('.nav-action[data-inbox]').forEach((action) => {
                    action.querySelector('.inbox-panel').hidden = true;
                    action.querySelector('.inbox-trigger').setAttribute('aria-expanded', 'false');
                });
            }
        });
    }
};

const initAccountMenu = () => {
    const root = document.getElementById('accountMenu');
    const button = document.getElementById('accountMenuButton');
    const menu = document.getElementById('accountDropdown');
    if (!root || !button || !menu || !PingPilot.initOnce(root, 'account-menu')) return;

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
    if (!form || !status || !PingPilot.initOnce(form, 'personalization')) return;

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

const initEnhancedNavigation = () => {
    if (window.PingPilotNavigation) return;

    const parser = new DOMParser();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    const isSkippableLink = (link, url) => {
        if (!link || link.dataset.enhancedNav === 'false') return true;
        if (link.target && link.target !== '_self') return true;
        if (link.hasAttribute('download')) return true;
        if (url.origin !== window.location.origin) return true;
        if (['/api/', '/static/', '/auth/'].some((prefix) => url.pathname.startsWith(prefix))) return true;
        if (url.pathname === '/logout') return true;
        if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return true;
        return false;
    };

    const closeTransientUi = () => {
        document.querySelectorAll('.search-results, .inbox-panel, .dropdown-menu').forEach((panel) => {
            panel.hidden = true;
        });
        document.querySelectorAll('[aria-expanded="true"]').forEach((node) => {
            if (node.matches('.inbox-trigger, #accountMenuButton, #globalSearchInput')) {
                node.setAttribute('aria-expanded', 'false');
            }
        });
        document.getElementById('sidebar')?.classList.remove('is-open');
        document.body.classList.remove('sidebar-open');
        document.getElementById('mobileMenuBtn')?.setAttribute('aria-expanded', 'false');
    };

    const waitForTransition = (element) => new Promise((resolve) => {
        if (reducedMotion.matches) {
            resolve();
            return;
        }
        let done = false;
        const finish = () => {
            if (done) return;
            done = true;
            element.removeEventListener('transitionend', finish);
            resolve();
        };
        element.addEventListener('transitionend', finish, { once: true });
        window.setTimeout(finish, 220);
    });

    const syncShell = (doc, nextUrl) => {
        document.title = doc.title || document.title;
        const nextTitle = doc.querySelector('.page-title');
        const currentTitle = document.querySelector('.page-title');
        if (nextTitle && currentTitle) currentTitle.innerHTML = nextTitle.innerHTML;

        document.querySelectorAll('.sidebar-nav a').forEach((link) => {
            const linkUrl = new URL(link.href, window.location.origin);
            link.classList.toggle('active', linkUrl.pathname === nextUrl.pathname);
        });
    };

    const replaceMain = (doc, nextUrl) => {
        const currentMain = document.getElementById('pageMain') || document.querySelector('main');
        const nextMain = doc.getElementById('pageMain') || doc.querySelector('main');
        if (!currentMain || !nextMain) throw new Error('The next page did not include a main content region.');

        const nextBodyClass = doc.body.className;
        currentMain.classList.add('page-exit');

        return waitForTransition(currentMain).then(() => {
            PingPilot.emitBeforePageSwap();
            document.body.className = nextBodyClass;
            currentMain.replaceWith(nextMain);
            syncShell(doc, nextUrl);
            closeTransientUi();

            nextMain.classList.add('page-enter');
            nextMain.focus({ preventScroll: true });
            window.setTimeout(() => nextMain.classList.remove('page-enter'), 280);

            if (nextUrl.hash) {
                document.querySelector(nextUrl.hash)?.scrollIntoView({ block: 'start' });
            } else {
                window.scrollTo({ top: 0, behavior: reducedMotion.matches ? 'auto' : 'smooth' });
            }

            PingPilot.emitPageReady();
        });
    };

    const go = async (target, options = {}) => {
        const nextUrl = new URL(target, window.location.href);
        document.body.classList.add('is-page-transitioning');
        try {
            const response = await fetch(nextUrl.href, {
                credentials: 'same-origin',
                headers: { Accept: 'text/html' },
            });
            const contentType = response.headers.get('content-type') || '';
            if (!response.ok || !contentType.includes('text/html')) throw new Error('Navigation fallback required.');

            const doc = parser.parseFromString(await response.text(), 'text/html');
            await replaceMain(doc, nextUrl);

            if (!options.fromPop) {
                const method = options.replace ? 'replaceState' : 'pushState';
                window.history[method]({ enhanced: true }, '', nextUrl.href);
            }
            return true;
        } catch (error) {
            if (!options.fromPop) window.location.assign(nextUrl.href);
            return false;
        } finally {
            document.body.classList.remove('is-page-transitioning');
        }
    };

    window.PingPilotNavigation = { go };
    window.history.replaceState({ enhanced: true }, '', window.location.href);

    document.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const link = event.target.closest('a[href]');
        if (!link) return;
        const url = new URL(link.href, window.location.href);
        if (isSkippableLink(link, url)) return;
        event.preventDefault();
        go(url.href);
    });

    window.addEventListener('popstate', () => {
        go(window.location.href, { replace: true, fromPop: true });
    });
};

const initApp = () => {
    initGlobalSearch();
    initTopbarInbox();
    initAccountMenu();
    initPersonalization();
    initEnhancedNavigation();
};

PingPilot.ready(() => {
    initApp();
    PingPilot.emitPageReady();
});

document.addEventListener('pingpilot:page-ready', () => {
    initPersonalization();
});
