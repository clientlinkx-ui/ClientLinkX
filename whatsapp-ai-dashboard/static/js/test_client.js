const initWhatsAppTestClient = () => {
    const root = document.querySelector('.test-client-page');
    if (!root || !window.PingPilot?.initOnce(root, 'whatsapp-test-client')) return;

    const fields = {
        name: document.getElementById('testCustomerName'),
        phone: document.getElementById('testCustomerPhone'),
        module: document.getElementById('testCustomerModule'),
        priority: document.getElementById('testCustomerPriority'),
        intent: document.getElementById('testCustomerIntent'),
        message: document.getElementById('testClientMessage'),
        form: document.getElementById('testClientForm'),
        timeline: document.getElementById('testClientTimeline'),
        openLink: document.getElementById('openConversationLink'),
        newCustomer: document.getElementById('newTestCustomer'),
        status: document.getElementById('testClientThreadStatus'),
        avatar: document.getElementById('phoneAvatar'),
        phoneName: document.getElementById('phoneCustomerName'),
        phoneMeta: document.getElementById('phoneCustomerMeta'),
        decisionCard: document.getElementById('testDecisionCard'),
        decisionLabel: document.getElementById('testDecisionLabel'),
        decisionProgress: document.getElementById('testDecisionProgress'),
        decisionConfidence: document.getElementById('testDecisionConfidence'),
        decisionReason: document.getElementById('testDecisionReason'),
        decisionFlags: document.getElementById('testDecisionFlags'),
    };
    let currentThreadId = null;

    const setStatus = (text, tone = 'neutral') => {
        fields.status.textContent = text;
        fields.status.classList.toggle('good', tone === 'good');
        fields.status.classList.toggle('warning', tone === 'warning');
        fields.status.classList.toggle('neutral-badge', tone === 'neutral');
    };

    const renderBubble = (message) => {
        const bubble = document.createElement('div');
        bubble.className = `phone-bubble ${message.role === 'customer' ? 'customer' : 'system'}`;
        const sender = document.createElement('span');
        sender.textContent = message.sender || (message.role === 'customer' ? fields.name.value : 'PingPilot');
        const body = document.createElement('p');
        body.textContent = message.body;
        bubble.append(sender, body);
        return bubble;
    };

    const renderTimeline = (thread) => {
        fields.timeline.replaceChildren(...(thread.messages_list || []).map(renderBubble));
        fields.timeline.scrollTop = fields.timeline.scrollHeight;
    };

    const renderDecision = (decision) => {
        const isEscalate = decision?.decision === 'escalate';
        fields.decisionCard.classList.toggle('warning-card', isEscalate);
        fields.decisionCard.classList.toggle('good-card', decision && !isEscalate);
        fields.decisionLabel.textContent = decision
            ? (isEscalate ? 'Escalate to human' : 'Continue chat')
            : 'Waiting for analysis';
        fields.decisionConfidence.textContent = decision ? `${decision.confidence}%` : '--';
        fields.decisionProgress.style.width = `${decision?.confidence || 0}%`;
        fields.decisionReason.textContent = decision?.reason || 'Send a message to run AI escalation analysis.';
        fields.decisionFlags.replaceChildren();
        const flags = decision?.risk_flags || [];
        if (!flags.length) {
            fields.decisionFlags.textContent = 'No risk flags detected';
        } else {
            flags.forEach((flag) => {
                const item = document.createElement('span');
                item.className = 'risk-flag';
                item.textContent = flag.replaceAll('_', ' ');
                fields.decisionFlags.appendChild(item);
            });
        }
    };

    const syncThread = (thread, decision) => {
        currentThreadId = thread.id;
        fields.avatar.textContent = thread.customer_name.charAt(0).toUpperCase();
        fields.phoneName.textContent = thread.customer_name;
        fields.phoneMeta.textContent = `${thread.phone} - ${thread.status} - ${thread.handler}`;
        fields.openLink.href = `/conversations#thread-${thread.id}`;
        setStatus(`${thread.status} thread`, thread.status === 'Escalated' ? 'warning' : 'good');
        renderTimeline(thread);
        renderDecision(decision || thread.ai_decision);
    };

    const payload = () => ({
        customer_name: fields.name.value.trim(),
        phone: fields.phone.value.trim(),
        module: fields.module.value,
        priority: fields.priority.value,
        intent: fields.intent.value.trim(),
        message: fields.message.value.trim(),
    });

    fields.form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const data = payload();
        if (!data.customer_name || !data.phone || !data.message) {
            CLX.toast('Enter a name, phone number, and message.', 'warning');
            return;
        }
        const button = fields.form.querySelector('button');
        button.disabled = true;
        try {
            const url = currentThreadId
                ? `/api/test-client/conversations/${currentThreadId}/messages`
                : '/api/test-client/conversations';
            const result = await CLX.json(url, { method: 'POST', body: JSON.stringify(data) });
            syncThread(result.thread, result.decision);
            fields.message.value = '';
            fields.message.focus();
            CLX.toast(result.message);
        } catch (error) {
            CLX.toast(error.message, 'warning');
        } finally {
            button.disabled = false;
        }
    });

    fields.newCustomer.addEventListener('click', () => {
        currentThreadId = null;
        fields.name.value = 'Test Customer';
        fields.phone.value = `+91 90000 ${Math.floor(10000 + Math.random() * 89999)}`;
        fields.intent.value = 'Test WhatsApp message';
        fields.priority.value = 'Normal';
        fields.timeline.innerHTML = `
            <div class="phone-empty-state">
                <i class="fa-brands fa-whatsapp"></i>
                <strong>No messages yet</strong>
                <span>Type a customer message below to create a real conversation thread.</span>
            </div>`;
        fields.phoneName.textContent = fields.name.value;
        fields.avatar.textContent = 'T';
        fields.phoneMeta.textContent = 'online - internal simulator';
        fields.openLink.href = '/conversations';
        setStatus('No thread', 'neutral');
        renderDecision(null);
        fields.message.focus();
    });

    fields.name.addEventListener('input', () => {
        const name = fields.name.value.trim() || 'Test Customer';
        fields.phoneName.textContent = name;
        fields.avatar.textContent = name.charAt(0).toUpperCase();
    });
};

window.PingPilot?.ready ? PingPilot.ready(initWhatsAppTestClient) : document.addEventListener('DOMContentLoaded', initWhatsAppTestClient);
document.addEventListener('pingpilot:page-ready', initWhatsAppTestClient);
