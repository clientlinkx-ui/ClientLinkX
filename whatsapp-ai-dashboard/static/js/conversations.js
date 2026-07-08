const initConversationFilters = () => {
    const filterButtons = [...document.querySelectorAll('[data-filter]')];
    const searchInput = document.getElementById('conversationSearch');
    const rows = [...document.querySelectorAll('.thread-row')];

    if (!filterButtons.length || !rows.length) {
        return;
    }

    let activeFilter = 'All';

    const applyFilters = () => {
        const query = (searchInput?.value || '').trim().toLowerCase();

        rows.forEach((row) => {
            const statusMatches = activeFilter === 'All' || row.dataset.status === activeFilter;
            const searchMatches = !query || row.dataset.search.toLowerCase().includes(query);
            row.hidden = !(statusMatches && searchMatches);
        });
    };

    filterButtons.forEach((button) => {
        button.addEventListener('click', () => {
            activeFilter = button.dataset.filter;
            filterButtons.forEach((item) => item.classList.toggle('active', item === button));
            applyFilters();
        });
    });

    rows.forEach((row) => {
        row.addEventListener('click', async () => {
            rows.forEach((item) => item.classList.toggle('active', item === row));
            await loadThread(row.dataset.threadId);
        });
    });

    searchInput?.addEventListener('input', applyFilters);

    let currentThreadId = document.querySelector('.thread-row.active')?.dataset.threadId || null;
    const timeline = document.getElementById('threadMessageTimeline');

    const bubble = (role, sender, body) => {
        const item = document.createElement('div');
        item.className = `message-bubble ${role === 'customer' ? 'inbound' : 'outbound'}`;
        item.innerHTML = `<span>${sender}</span><p></p>`;
        item.querySelector('p').textContent = body;
        return item;
    };

    async function loadThread(threadId) {
        if (!threadId || !timeline) return;
        currentThreadId = threadId;
        try {
            const response = await fetch(`/api/conversations/${threadId}`);
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || 'Could not load thread.');
            const thread = data.thread;
            document.getElementById('threadDetailName').textContent = thread.customer_name;
            document.getElementById('threadDetailAvatar').textContent = thread.customer_name.charAt(0);
            document.getElementById('threadDetailPhone').textContent = thread.phone;
            document.getElementById('threadDetailMeta').textContent = `${thread.module} - ${thread.sentiment} sentiment - SLA ${thread.sla}`;
            document.getElementById('threadDetailHandler').textContent = `${thread.handler} handling`;
            timeline.replaceChildren(...thread.messages_list.map((message) => bubble(message.role, message.sender, message.body)));
        } catch (error) {
            window.CLX?.toast ? CLX.toast(error.message, 'warning') : window.alert(error.message);
        }
    }

    document.getElementById('sendThreadReply')?.addEventListener('click', async () => {
        const input = document.getElementById('threadReplyInput');
        const body = input.value.trim();
        if (!body || !currentThreadId) return input.focus();
        try {
            const response = await fetch(`/api/conversations/${currentThreadId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ body }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || 'Could not send reply.');
            timeline.appendChild(bubble(data.conversation_message.role, data.conversation_message.sender, data.conversation_message.body));
            input.value = '';
            window.CLX?.toast?.(data.message);
        } catch (error) {
            window.CLX?.toast ? CLX.toast(error.message, 'warning') : window.alert(error.message);
        }
    });

    document.getElementById('assignThread')?.addEventListener('click', async () => {
        if (!currentThreadId) return;
        await fetch(`/api/conversations/${currentThreadId}/assign`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ owner: 'Support Desk' }) });
        window.CLX?.toast?.('Conversation assigned.');
    });
    document.getElementById('resolveThread')?.addEventListener('click', async () => {
        if (!currentThreadId) return;
        await fetch(`/api/conversations/${currentThreadId}/resolve`, { method: 'POST' });
        window.CLX?.toast?.('Conversation resolved.');
    });
    document.getElementById('escalateThread')?.addEventListener('click', async () => {
        if (!currentThreadId) return;
        await fetch(`/api/conversations/${currentThreadId}/escalate`, { method: 'POST' });
        window.CLX?.toast?.('Conversation escalated.');
    });

    document.getElementById('newConversationThread')?.addEventListener('click', () => {
        if (!window.CLX) return;
        CLX.modal('New Thread', [
            { name: 'customer_name', label: 'Customer name' },
            { name: 'phone', label: 'Phone' },
            { name: 'intent', label: 'Intent', value: 'General enquiry' },
            { name: 'module', label: 'Module', options: ['Support', 'Sales', 'Admissions', 'Appointments', 'Orders'] },
            { name: 'message', label: 'First message', type: 'textarea', full: true },
        ], async (payload) => {
            const data = await CLX.json('/api/conversations', { method: 'POST', body: JSON.stringify(payload) });
            CLX.toast(data.message);
            setTimeout(() => location.reload(), 500);
        });
    });

    if (currentThreadId) loadThread(currentThreadId);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initConversationFilters);
} else {
    initConversationFilters();
}
