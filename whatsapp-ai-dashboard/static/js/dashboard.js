const fillProgressBars = () => {
    document.querySelectorAll('.progress-fill').forEach((fill) => {
        const progress = Number(fill.dataset.progress) || 0;
        fill.style.width = '0%';
        requestAnimationFrame(() => {
            fill.style.width = `${progress}%`;
        });
    });
};

const dashboardJson = async (url, options = {}) => {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
        throw new Error(data.error || 'Dashboard data is temporarily unavailable.');
    }
    return data;
};

const chartState = (panel, message = '', visible = false) => {
    const state = panel?.querySelector('[data-chart-state]');
    if (!state) return;
    state.textContent = message;
    state.hidden = !visible;
};

const setPanelLoading = (panel, loading) => {
    panel?.classList.toggle('is-loading', loading);
};

const updateLastUpdated = (updatedAt) => {
    const stamp = document.getElementById('dashboardLastUpdated');
    if (stamp && updatedAt) stamp.textContent = `Updated ${updatedAt}`;
};

const loadTraffic = async (range = '7d') => {
    const panel = document.querySelector('.traffic-panel');
    setPanelLoading(panel, true);
    chartState(panel, 'Loading traffic...', true);
    try {
        const data = await dashboardJson(`/api/dashboard/traffic?range=${encodeURIComponent(range)}`);
        window.PingPilotCharts?.renderTrafficChart(range, data.data);
        updateLastUpdated(data.updated_at);
        chartState(panel);
    } catch (error) {
        chartState(panel, error.message, true);
        window.CLX?.toast?.(error.message, 'warning');
    } finally {
        setPanelLoading(panel, false);
    }
};

const loadStatusBreakdown = async () => {
    const panel = document.querySelector('.status-panel');
    setPanelLoading(panel, true);
    chartState(panel, 'Loading status...', true);
    try {
        const data = await dashboardJson('/api/dashboard/status-breakdown');
        window.PingPilotCharts?.renderStatusChart(data.data);
        updateLastUpdated(data.updated_at);
        chartState(panel);
    } catch (error) {
        chartState(panel, error.message, true);
    } finally {
        setPanelLoading(panel, false);
    }
};

const initDashboardActions = () => {
    const root = document.querySelector('.dashboard');
    if (!root || !window.PingPilot?.initOnce(root, 'dashboard-actions')) return;

    document.querySelectorAll('.traffic-panel [data-range]').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.traffic-panel [data-range]').forEach((item) => item.classList.toggle('active', item === button));
            loadTraffic(button.dataset.range);
        });
    });

    document.getElementById('dashboardRefresh')?.addEventListener('click', async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        button.classList.add('is-spinning');
        try {
            const range = document.querySelector('.traffic-panel [data-range].active')?.dataset.range || '7d';
            const data = await dashboardJson('/api/dashboard/refresh', { method: 'POST', body: '{}' });
            window.PingPilotCharts?.renderTrafficChart(range, data.data.traffic);
            window.PingPilotCharts?.renderStatusChart(data.data.status_breakdown);
            updateLastUpdated(data.updated_at);
            window.CLX?.toast?.('Dashboard refreshed.');
        } catch (error) {
            window.CLX?.toast?.(error.message, 'warning');
        } finally {
            button.disabled = false;
            button.classList.remove('is-spinning');
        }
    });

    document.getElementById('dashboardExportReport')?.addEventListener('click', () => {
        window.location.assign('/api/dashboard/export');
    });

    const activeRange = document.querySelector('.traffic-panel [data-range].active')?.dataset.range || '7d';
    loadTraffic(activeRange);
    loadStatusBreakdown();
};

const initDashboardHelp = () => {
    const root = document.querySelector('.dashboard');
    if (!root || !window.PingPilot?.initOnce(root, 'dashboard-help')) return;

    const popover = document.createElement('div');
    popover.className = 'dashboard-help-popover';
    popover.hidden = true;
    document.body.appendChild(popover);
    let hideTimer;
    let showTimer;
    const hoverDelay = 1200;

    const show = (element) => {
        const text = element.dataset.help;
        if (!text) return;
        window.clearTimeout(hideTimer);
        popover.textContent = text;
        popover.hidden = false;
        const rect = element.getBoundingClientRect();
        const top = Math.max(12, rect.top + window.scrollY - popover.offsetHeight - 12);
        const left = Math.min(
            window.scrollX + window.innerWidth - popover.offsetWidth - 12,
            Math.max(12, rect.left + window.scrollX)
        );
        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;
        requestAnimationFrame(() => popover.classList.add('is-visible'));
    };

    const hide = () => {
        window.clearTimeout(showTimer);
        popover.classList.remove('is-visible');
        window.clearTimeout(hideTimer);
        hideTimer = window.setTimeout(() => {
            if (!popover.classList.contains('is-visible')) popover.hidden = true;
        }, 180);
    };

    root.querySelectorAll('[data-help]').forEach((element) => {
        element.setAttribute('tabindex', element.getAttribute('tabindex') || '0');
        element.addEventListener('mouseenter', () => {
            window.clearTimeout(showTimer);
            showTimer = window.setTimeout(() => show(element), hoverDelay);
        });
        element.addEventListener('focus', () => show(element));
        element.addEventListener('mouseleave', hide);
        element.addEventListener('blur', hide);
    });

    window.addEventListener('scroll', hide, { passive: true });
};

const initDashboard = () => {
    fillProgressBars();
    initDashboardActions();
    initDashboardHelp();
};

window.PingPilot?.ready ? PingPilot.ready(initDashboard) : document.addEventListener('DOMContentLoaded', initDashboard);
document.addEventListener('pingpilot:page-ready', initDashboard);
