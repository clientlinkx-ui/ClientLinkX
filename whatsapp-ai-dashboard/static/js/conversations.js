const initConversationFilters = () => {
    const root = document.querySelector('.conversations-page');
    if (!root || !window.PingPilot?.initOnce(root, 'conversations')) return;

    const state = {
        activeFilter: 'All',
        currentThreadId: new URLSearchParams(window.location.search).get('thread'),
        threads: [],
        selectedThread: null,
        assignees: { teams: [], members: [] },
        loading: false,
    };

    const els = {
        filterButtons: [...root.querySelectorAll('[data-filter]')],
        search: document.getElementById('conversationSearch'),
        module: document.getElementById('conversationModuleFilter'),
        assignee: document.getElementById('conversationAssigneeFilter'),
        threadList: document.getElementById('threadList'),
        threadEmpty: document.getElementById('threadListEmpty'),
        queueBody: document.getElementById('conversationQueueBody'),
        queueEmpty: document.getElementById('conversationQueueEmpty'),
        shownCount: document.getElementById('threadShownCount'),
        timeline: document.getElementById('threadMessageTimeline'),
        replyInput: document.getElementById('threadReplyInput'),
        sendReply: document.getElementById('sendThreadReply'),
        assign: document.getElementById('assignThread'),
        resolve: document.getElementById('resolveThread'),
        escalate: document.getElementById('escalateThread'),
        analyze: document.getElementById('analyzeThread'),
        continue: document.getElementById('continueThread'),
        aiEscalate: document.getElementById('aiEscalateThread'),
        export: document.getElementById('exportConversations'),
        tableToggle: document.getElementById('toggleConversationTable'),
        queuePanel: document.getElementById('conversationQueuePanel'),
        newThread: document.getElementById('newConversationThread'),
        detailName: document.getElementById('threadDetailName'),
        detailAvatar: document.getElementById('threadDetailAvatar'),
        detailPhone: document.getElementById('threadDetailPhone'),
        detailMeta: document.getElementById('threadDetailMeta'),
        detailAssignee: document.getElementById('threadDetailAssignee'),
        detailHandler: document.getElementById('threadDetailHandler'),
        decision: {
            mode: document.getElementById('aiDecisionMode'),
            card: document.getElementById('aiDecisionCard'),
            label: document.getElementById('aiDecisionLabel'),
            confidence: document.getElementById('aiDecisionConfidence'),
            progress: document.getElementById('aiDecisionProgress'),
            model: document.getElementById('aiDecisionModel'),
            reason: document.getElementById('aiDecisionReason'),
            action: document.getElementById('aiDecisionAction'),
            flags: document.getElementById('aiDecisionFlags'),
        },
    };

    const json = async (url, options = {}) => {
        if (window.CLX?.json) return CLX.json(url, options);
        const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Request failed.');
        return data;
    };

    const toast = (message, tone = 'good') => window.CLX?.toast ? CLX.toast(message, tone) : window.alert(message);

    const params = () => {
        const search = new URLSearchParams();
        if (state.activeFilter && state.activeFilter !== 'All') search.set('status', state.activeFilter);
        if (els.search?.value.trim()) search.set('q', els.search.value.trim());
        if (els.module?.value) search.set('module', els.module.value);
        if (els.assignee?.value) search.set('assignee', els.assignee.value);
        if (state.currentThreadId) search.set('thread', state.currentThreadId);
        return search;
    };

    const statusClass = (status = '') => `conversation-status ${status.toLowerCase()}`;
    const iconForHandler = (handler) => handler === 'AI' ? 'fa-solid fa-robot' : 'fa-solid fa-user';
    const escape = (value) => {
        const span = document.createElement('span');
        span.textContent = value ?? '';
        return span.innerHTML;
    };

    const updateActionAvailability = () => {
        const thread = state.selectedThread;
        const hasThread = Boolean(thread);
        [els.sendReply, els.assign, els.escalate, els.analyze, els.aiEscalate].forEach((button) => {
            if (button) button.disabled = !hasThread;
        });
        if (els.replyInput) els.replyInput.disabled = !hasThread || thread?.status === 'Resolved';
        if (els.resolve) els.resolve.disabled = !hasThread || thread?.status === 'Resolved';
        if (els.continue) els.continue.disabled = !hasThread || !['Resolved', 'Escalated'].includes(thread?.status);
    };

    const setLoading = (loading) => {
        state.loading = loading;
        root.classList.toggle('is-loading', loading);
        if (loading) {
            [els.sendReply, els.assign, els.resolve, els.escalate, els.analyze, els.continue, els.aiEscalate].forEach((button) => {
                if (button) button.disabled = true;
            });
        } else {
            updateActionAvailability();
        }
    };

    const updateUrl = () => {
        const url = new URL(window.location.href);
        if (state.currentThreadId) url.searchParams.set('thread', state.currentThreadId);
        else url.searchParams.delete('thread');
        window.history.replaceState({}, '', url);
    };

    const renderThreadList = () => {
        const existingEmpty = els.threadEmpty;
        els.threadList.querySelectorAll('.thread-row').forEach((row) => row.remove());
        state.threads.forEach((thread) => {
            const row = document.createElement('button');
            row.className = `thread-row${String(thread.id) === String(state.currentThreadId) ? ' active' : ''}`;
            row.type = 'button';
            row.dataset.threadId = thread.id;
            row.dataset.status = thread.status;
            row.dataset.assignee = thread.assignee;
            row.innerHTML = `
                <span class="avatar-placeholder">${escape(thread.customer_name?.charAt(0) || '?')}</span>
                <span class="thread-main">
                    <span class="thread-top"><strong>${escape(thread.customer_name)}</strong><small>${escape(thread.time)}</small></span>
                    <span class="thread-message">${escape(thread.last_message)}</span>
                    <span class="conversation-meta">
                        <span class="handler"><i class="${iconForHandler(thread.handler)}"></i> ${escape(thread.handler)}</span>
                        <span class="${statusClass(thread.status)}">${escape(thread.status)}</span>
                        <span class="thread-priority ${(thread.priority || '').toLowerCase()}">${escape(thread.priority)}</span>
                        <span class="thread-assignee">${escape(thread.assignee)}</span>
                    </span>
                </span>
            `;
            row.addEventListener('click', () => selectThread(thread.id));
            els.threadList.insertBefore(row, existingEmpty);
        });
        els.threadEmpty.hidden = state.threads.length > 0;
        els.shownCount.textContent = `${state.threads.length} shown`;
    };

    const renderQueue = () => {
        els.queueBody.replaceChildren();
        state.threads.forEach((thread) => {
            const row = document.createElement('tr');
            row.dataset.threadId = thread.id;
            row.className = String(thread.id) === String(state.currentThreadId) ? 'active-row' : '';
            row.innerHTML = `
                <td><strong>${escape(thread.customer_name)}</strong><span>${escape(thread.phone)}</span></td>
                <td>${escape(thread.intent)}</td>
                <td>${escape(thread.module)}</td>
                <td><span class="${statusClass(thread.status)}">${escape(thread.status)}</span></td>
                <td>${escape(thread.messages)}</td>
                <td>${escape(thread.sla)}</td>
            `;
            row.addEventListener('click', () => selectThread(thread.id));
            els.queueBody.appendChild(row);
        });
        els.queueEmpty.hidden = state.threads.length > 0;
    };

    const renderSummary = (counts = {}) => {
        const values = {
            'Open Threads': counts.total ?? 0,
            'Waiting on Customer': counts.waiting ?? 0,
            Escalated: counts.escalated ?? 0,
            'AI Resolved Today': counts.resolved ?? 0,
        };
        root.querySelectorAll('[data-summary-label]').forEach((card) => {
            const value = values[card.dataset.summaryLabel];
            const target = card.querySelector('[data-summary-value]');
            if (target && value !== undefined) target.textContent = Number(value).toLocaleString();
        });
    };

    const bubble = (message) => {
        const role = message.role || 'agent';
        const item = document.createElement('div');
        item.className = `message-bubble ${role === 'customer' ? 'inbound' : role === 'system' ? 'system' : 'outbound'}`;
        item.innerHTML = `<span>${escape(message.sender)} <time>${escape(message.created_at || '')}</time></span><p></p>`;
        item.querySelector('p').textContent = message.body || '';
        return item;
    };

    const renderDecision = (decision) => {
        const hasDecision = Boolean(decision);
        const isEscalate = decision?.decision === 'escalate';
        els.decision.card?.classList.toggle('warning-card', hasDecision && isEscalate);
        els.decision.card?.classList.toggle('good-card', hasDecision && !isEscalate);
        els.decision.label.textContent = hasDecision ? (isEscalate ? 'Escalate to human' : 'Continue chat') : 'Analysis pending';
        els.decision.confidence.textContent = hasDecision ? `${decision.confidence}%` : '--';
        els.decision.progress.style.width = `${decision?.confidence || 0}%`;
        els.decision.progress.dataset.progress = String(decision?.confidence || 0);
        els.decision.progress.classList.toggle('warning-fill', hasDecision && decision.confidence < 70);
        els.decision.model.textContent = hasDecision ? `${decision.model || 'Model'} - ${decision.updated_at || decision.created_at || 'just now'}` : 'Not analyzed';
        els.decision.reason.textContent = decision?.reason || 'AI routing has not reviewed this thread yet.';
        els.decision.action.textContent = decision?.suggested_action || 'Run analysis to get the next best action.';
        els.decision.mode.textContent = decision?.mode === 'auto' ? 'Auto mode' : 'Recommend';
        els.decision.flags.replaceChildren();
        const flags = decision?.risk_flags || [];
        if (!flags.length) {
            els.decision.flags.textContent = hasDecision ? 'None detected' : 'None yet';
            return;
        }
        flags.forEach((flag) => {
            const item = document.createElement('span');
            item.className = 'risk-flag';
            item.textContent = String(flag).replaceAll('_', ' ');
            els.decision.flags.appendChild(item);
        });
    };

    const renderDetail = (thread) => {
        state.selectedThread = thread;
        state.currentThreadId = thread?.id ? String(thread.id) : null;
        updateUrl();
        renderThreadList();
        renderQueue();
        if (!thread) {
            els.detailName.textContent = 'Select a thread';
            els.detailAvatar.textContent = '--';
            els.detailPhone.textContent = 'No thread selected';
            els.detailMeta.textContent = 'Select a conversation to view details.';
            els.detailAssignee.textContent = 'Unassigned';
            els.replyInput.disabled = true;
            els.timeline.innerHTML = '<div class="empty-state">Select a thread to view the message timeline.</div>';
            renderDecision(null);
            updateActionAvailability();
            return;
        }
        els.detailName.textContent = thread.customer_name;
        els.detailAvatar.textContent = thread.customer_name?.charAt(0) || '?';
        els.detailPhone.textContent = thread.phone;
        els.detailMeta.textContent = `${thread.module} - ${thread.sentiment} sentiment - SLA ${thread.sla}`;
        els.detailAssignee.textContent = `Assigned to ${thread.assignee}`;
        els.detailHandler.textContent = `${thread.handler} handling`;
        els.detailHandler.className = `status-pill ${thread.status === 'Resolved' ? 'neutral-badge' : 'online'}`;
        els.timeline.replaceChildren(...(thread.messages_list || []).map(bubble));
        if (!(thread.messages_list || []).length) {
            els.timeline.innerHTML = '<div class="empty-state">No messages recorded yet.</div>';
        }
        renderDecision(thread.ai_decision);
        els.timeline.scrollTop = els.timeline.scrollHeight;
        updateActionAvailability();
    };

    const loadThread = async (threadId) => {
        if (!threadId) return renderDetail(null);
        setLoading(true);
        try {
            const data = await json(`/api/conversations/${threadId}`);
            renderDetail(data.thread);
        } catch (error) {
            toast(error.message, 'warning');
            renderDetail(null);
        } finally {
            setLoading(false);
        }
    };

    const loadQueue = async () => {
        setLoading(true);
        try {
            const data = await json(`/api/conversations?${params().toString()}`);
            state.threads = data.threads || [];
            state.assignees = data.assignees || state.assignees;
            renderSummary(data.summary_counts || {});
            renderThreadList();
            renderQueue();
            if (data.selected_thread) renderDetail(data.selected_thread);
            else renderDetail(null);
        } catch (error) {
            toast(error.message, 'warning');
        } finally {
            setLoading(false);
        }
    };

    const selectThread = async (threadId) => {
        state.currentThreadId = String(threadId);
        renderThreadList();
        renderQueue();
        await loadThread(threadId);
    };

    const refreshSelectedThread = (thread) => {
        if (!thread) return;
        state.threads = state.threads.map((item) => String(item.id) === String(thread.id) ? { ...item, ...thread } : item);
        renderDetail(thread);
    };

    const analyzeThread = async (showToast = false) => {
        if (!state.currentThreadId) return;
        els.analyze.disabled = true;
        els.analyze.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing';
        renderDecision({
            decision: 'continue',
            confidence: 0,
            reason: 'Analyzing latest messages...',
            suggested_action: 'Checking handoff rules, sentiment, confidence, and guardrails.',
            risk_flags: [],
            mode: 'recommend',
            model: 'Pending',
        });
        try {
            const data = await json(`/api/conversations/${state.currentThreadId}/ai-decision`, { method: 'POST' });
            renderDecision(data.decision);
            if (data.thread) refreshSelectedThread(data.thread);
            if (showToast) toast(data.message);
        } catch (error) {
            toast(error.message, 'warning');
        } finally {
            els.analyze.disabled = false;
            els.analyze.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze';
        }
    };

    const sendReply = async () => {
        const body = els.replyInput.value.trim();
        if (!body) {
            els.replyInput.focus();
            toast('Enter a message.', 'warning');
            return;
        }
        if (!state.currentThreadId) return;
        try {
            const data = await json(`/api/conversations/${state.currentThreadId}/messages`, {
                method: 'POST',
                body: JSON.stringify({ body }),
            });
            els.replyInput.value = '';
            if (data.thread) {
                refreshSelectedThread(data.thread);
            } else if (data.conversation_message) {
                els.timeline.appendChild(bubble(data.conversation_message));
                els.timeline.scrollTop = els.timeline.scrollHeight;
            }
            toast(data.message);
            await analyzeThread(false);
        } catch (error) {
            toast(error.message, 'warning');
        }
    };

    const statusAction = async (action, label) => {
        if (!state.currentThreadId) return;
        try {
            const data = await json(`/api/conversations/${state.currentThreadId}/${action}`, { method: 'POST' });
            refreshSelectedThread(data.thread);
            renderDecision(data.decision || data.thread?.ai_decision);
            toast(data.message || label);
        } catch (error) {
            toast(error.message, 'warning');
        }
    };

    const assignThread = () => {
        if (!state.currentThreadId || !window.CLX) return;
        const teamOptions = [{ label: 'Support Desk', value: 'Support Desk' }, ...state.assignees.teams.map((team) => ({ label: team.name, value: team.name }))];
        const memberOptions = [{ label: 'No specific member', value: '' }, ...state.assignees.members.map((member) => ({ label: `${member.name} - ${member.team}`, value: String(member.id) }))];
        CLX.modal('Assign Conversation', [
            { name: 'assigned_team', label: 'Team', options: teamOptions, value: state.selectedThread?.assigned_team || 'Support Desk' },
            { name: 'assigned_user_id', label: 'Team member', options: memberOptions, value: String(state.selectedThread?.assigned_user_id || '') },
        ], async (payload) => {
            const data = await json(`/api/conversations/${state.currentThreadId}/assign`, {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            refreshSelectedThread(data.thread);
            renderDecision(data.decision || data.thread?.ai_decision);
            toast(data.message);
        });
    };

    const debounce = (fn, delay = 240) => {
        let timer;
        return (...args) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => fn(...args), delay);
        };
    };

    const setTableView = (open) => {
        if (!els.tableToggle || !els.queuePanel) return;
        els.queuePanel.hidden = !open;
        els.tableToggle.setAttribute('aria-expanded', String(open));
        els.tableToggle.classList.toggle('active', open);
    };

    els.filterButtons.forEach((button) => {
        button.addEventListener('click', () => {
            state.activeFilter = button.dataset.filter;
            state.currentThreadId = null;
            els.filterButtons.forEach((item) => item.classList.toggle('active', item === button));
            loadQueue();
        });
    });
    els.search?.addEventListener('input', debounce(() => { state.currentThreadId = null; loadQueue(); }));
    els.module?.addEventListener('change', () => { state.currentThreadId = null; loadQueue(); });
    els.assignee?.addEventListener('change', () => { state.currentThreadId = null; loadQueue(); });
    els.sendReply?.addEventListener('click', sendReply);
    els.replyInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendReply();
        }
    });
    els.assign?.addEventListener('click', assignThread);
    els.resolve?.addEventListener('click', () => statusAction('resolve', 'Conversation resolved.'));
    els.escalate?.addEventListener('click', () => statusAction('escalate', 'Conversation escalated.'));
    els.aiEscalate?.addEventListener('click', () => statusAction('escalate', 'Conversation escalated.'));
    els.continue?.addEventListener('click', () => statusAction('continue', 'Conversation continued.'));
    els.analyze?.addEventListener('click', () => analyzeThread(true));
    els.export?.addEventListener('click', () => {
        window.location.assign(`/api/conversations/export?${params().toString()}`);
    });
    els.tableToggle?.addEventListener('click', () => {
        setTableView(els.queuePanel?.hidden !== false);
    });
    els.newThread?.addEventListener('click', () => {
        if (!window.CLX) return;
        CLX.modal('New Thread', [
            { name: 'customer_name', label: 'Customer name' },
            { name: 'phone', label: 'Phone' },
            { name: 'intent', label: 'Intent', value: 'General enquiry' },
            { name: 'module', label: 'Module', options: ['Support', 'Sales', 'Admissions', 'Appointments', 'Orders'] },
            { name: 'priority', label: 'Priority', options: ['Normal', 'High', 'Urgent'] },
            { name: 'message', label: 'First message', type: 'textarea', full: true },
        ], async (payload) => {
            const data = await json('/api/conversations', { method: 'POST', body: JSON.stringify(payload) });
            state.currentThreadId = String(data.thread.id);
            toast(data.message);
            await loadQueue();
        });
    });

    loadQueue();
};

window.PingPilot?.ready ? PingPilot.ready(initConversationFilters) : document.addEventListener('DOMContentLoaded', initConversationFilters);
document.addEventListener('pingpilot:page-ready', initConversationFilters);
