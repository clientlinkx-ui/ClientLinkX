const initAssistantSimulator = () => {
    const providerSelect = document.getElementById('assistantProvider');
    const apiKeyInput = document.getElementById('assistantApiKey');
    const apiUrlInput = document.getElementById('assistantApiUrl');
    const modelInput = document.getElementById('assistantModel');
    const saveButton = document.getElementById('saveAssistantKey');
    const sendButton = document.getElementById('runAssistantTest');
    const messageInput = document.getElementById('assistantSimulatorInput');
    const timeline = document.getElementById('assistantSimulatorMessages');
    const statusBadge = document.getElementById('ollamaStatus');

    if (!providerSelect || !apiKeyInput || !apiUrlInput || !modelInput || !saveButton || !sendButton || !messageInput || !timeline || !statusBadge) {
        return;
    }

    const providerDefaults = {
        ollama: {
            label: 'Ollama',
            model: 'llama3.1',
            apiUrl: 'https://ollama.com/api/chat',
        },
        openrouter: {
            label: 'OpenRouter',
            model: 'openai/gpt-4o-mini',
            apiUrl: 'https://openrouter.ai/api/v1/chat/completions',
        },
    };

    const history = [
        { role: 'user', content: 'Can I reschedule my appointment to Saturday?' },
        { role: 'assistant', content: 'Yes. I can help with that. Please share your current booking ID or registered phone number.' },
    ];

    const setStatus = (message, tone = 'neutral') => {
        statusBadge.textContent = message;
        statusBadge.classList.toggle('good', tone === 'good');
        statusBadge.classList.toggle('warning', tone === 'warning');
        statusBadge.classList.toggle('neutral-badge', tone === 'neutral');
    };

    providerSelect.addEventListener('change', () => {
        const defaults = providerDefaults[providerSelect.value] || providerDefaults.ollama;
        modelInput.value = defaults.model;
        apiUrlInput.value = defaults.apiUrl;
        apiKeyInput.placeholder = `Paste your ${defaults.label} API key`;
        setStatus(`${defaults.label} selected`, 'neutral');
    });

    const appendMessage = (role, label, content) => {
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${role === 'assistant' ? 'outbound' : 'inbound'}`;

        const sender = document.createElement('span');
        sender.textContent = label;

        const text = document.createElement('p');
        text.textContent = content;

        bubble.append(sender, text);
        timeline.appendChild(bubble);
        timeline.scrollTop = timeline.scrollHeight;
    };

    const postJson = async (url, payload) => {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.ok) {
            throw new Error(data.error || 'The simulator request failed.');
        }
        return data;
    };

    saveButton.addEventListener('click', async () => {
        saveButton.disabled = true;
        setStatus('Connecting...', 'warning');

        try {
            const data = await postJson('/api/assistant/config', {
                provider: providerSelect.value,
                api_key: apiKeyInput.value,
                api_url: apiUrlInput.value,
                model: modelInput.value,
            });
            apiKeyInput.value = '';
            setStatus(`${data.provider_label}: ${data.model}`, 'good');
        } catch (error) {
            setStatus(error.message, 'warning');
        } finally {
            saveButton.disabled = false;
        }
    });

    const sendMessage = async () => {
        const message = messageInput.value.trim();
        if (!message) {
            messageInput.focus();
            return;
        }

        messageInput.value = '';
        sendButton.disabled = true;
        appendMessage('user', 'Test user', message);
        setStatus('Thinking...', 'warning');

        try {
            const data = await postJson('/api/assistant/chat', {
                message,
                history,
            });
            history.push({ role: 'user', content: message });
            history.push({ role: 'assistant', content: data.reply });
            appendMessage('assistant', `${data.provider_label} - ${data.model}`, data.reply);
            setStatus(`${data.provider_label}: ${data.model}`, 'good');
        } catch (error) {
            appendMessage('assistant', 'Simulator error', error.message);
            setStatus('Needs attention', 'warning');
        } finally {
            sendButton.disabled = false;
            messageInput.focus();
        }
    };

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAssistantSimulator);
} else {
    initAssistantSimulator();
}

const aiJson = async (url, options = {}) => {
    const response = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || 'The request could not be completed.');
    return data;
};

const setBadge = (element, message, tone = 'neutral') => {
    if (!element) return;
    element.textContent = message;
    element.classList.toggle('good', tone === 'good');
    element.classList.toggle('warning', tone === 'warning');
    element.classList.toggle('neutral-badge', tone === 'neutral');
};

const appendBubble = (timeline, role, label, content) => {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${role === 'assistant' ? 'outbound' : 'inbound'}`;
    const sender = document.createElement('span');
    sender.textContent = label;
    const text = document.createElement('p');
    text.textContent = content;
    bubble.append(sender, text);
    timeline.appendChild(bubble);
    timeline.scrollTop = timeline.scrollHeight;
};

const initAiManagement = () => {
    const save = document.getElementById('saveAiRuntime');
    const deploy = document.getElementById('deployAiRuntime');
    const status = document.getElementById('aiRuntimeStatus');
    const runtimePayload = () => ({
        primary_model: document.getElementById('aiPrimaryModel').value.trim(),
        fallback_model: document.getElementById('aiFallbackModel').value.trim(),
        confidence_threshold: Number(document.getElementById('aiConfidence').value),
        temperature: Number(document.getElementById('aiTemperature').value),
        system_prompt: document.getElementById('aiSystemPrompt').value.trim(),
    });
    save?.addEventListener('click', async () => {
        save.disabled = true;
        try {
            const data = await aiJson('/api/ai/runtime', { method: 'POST', body: JSON.stringify(runtimePayload()) });
            setBadge(status, data.message, 'good');
        } catch (error) { setBadge(status, error.message, 'warning'); }
        finally { save.disabled = false; }
    });
    deploy?.addEventListener('click', async () => {
        deploy.disabled = true;
        try {
            await aiJson('/api/ai/runtime', { method: 'POST', body: JSON.stringify(runtimePayload()) });
            const data = await aiJson('/api/ai/deploy', { method: 'POST' });
            setBadge(status, data.message, 'good');
        } catch (error) { setBadge(status, error.message, 'warning'); }
        finally { deploy.disabled = false; }
    });
    document.querySelectorAll('.ai-guardrail-toggle').forEach((toggle) => {
        toggle.addEventListener('change', async () => {
            try {
                await aiJson(`/api/ai/guardrails/${toggle.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: toggle.checked }) });
            } catch (error) { toggle.checked = !toggle.checked; setBadge(status, error.message, 'warning'); }
        });
    });
    document.getElementById('runAiTestSuite')?.addEventListener('click', () => {
        document.getElementById('assistantSimulatorInput')?.focus();
        setBadge(document.getElementById('ollamaStatus'), 'Send a test message to run against the connected model', 'neutral');
    });
};

const initPromptBuilder = () => {
    const cards = [...document.querySelectorAll('.prompt-resource')];
    if (!document.getElementById('promptName')) return;
    let currentId = null;
    const fields = {
        name: document.getElementById('promptName'), module: document.getElementById('promptModule'),
        version: document.getElementById('promptVersion'), target: document.getElementById('promptTarget'),
        instructions: document.getElementById('promptInstructions'), status: document.getElementById('promptStatus'),
    };
    const load = (prompt = {}) => {
        currentId = prompt.id || null;
        fields.name.value = prompt.name || '';
        fields.module.value = prompt.module || 'Support';
        fields.version.value = prompt.version || 'v1.0';
        fields.target.value = prompt.deployment_target || 'Staging';
        fields.instructions.value = prompt.instructions || '';
        document.getElementById('promptEditorTitle').textContent = prompt.name || 'New Prompt';
        setBadge(fields.status, prompt.status || 'New draft', prompt.status === 'Live' ? 'good' : 'neutral');
        cards.forEach((card) => card.classList.toggle('selected', Number(card.dataset.promptId) === currentId));
    };
    cards.forEach((card) => {
        const prompt = JSON.parse(card.dataset.prompt);
        card.dataset.promptId = prompt.id;
        card.addEventListener('click', () => load(prompt));
    });
    const savePrompt = async (publish = false) => {
        const button = publish ? document.getElementById('publishPrompt') : document.getElementById('savePrompt');
        button.disabled = true;
        try {
            const data = await aiJson('/api/prompts', { method: 'POST', body: JSON.stringify({
                id: currentId, name: fields.name.value.trim(), module: fields.module.value,
                version: fields.version.value.trim(), deployment_target: publish ? 'Production' : fields.target.value,
                instructions: fields.instructions.value.trim(), status: publish ? 'Live' : 'Draft',
            }) });
            currentId = data.prompt.id;
            setBadge(fields.status, publish ? 'Published to production' : data.message, publish ? 'good' : 'neutral');
            if (!cards.some((card) => Number(card.dataset.promptId) === currentId)) setTimeout(() => location.reload(), 350);
        } catch (error) { setBadge(fields.status, error.message, 'warning'); }
        finally { button.disabled = false; }
    };
    document.getElementById('newPrompt').addEventListener('click', () => load());
    document.getElementById('savePrompt').addEventListener('click', () => savePrompt(false));
    document.getElementById('publishPrompt').addEventListener('click', () => savePrompt(true));
    document.getElementById('previewPrompt').addEventListener('click', () => fields.instructions.focus());
    const runTest = async () => {
        const input = document.getElementById('promptTestInput');
        const timeline = document.getElementById('promptTestMessages');
        const button = document.getElementById('runPromptTest');
        const message = input.value.trim();
        if (!message) return input.focus();
        appendBubble(timeline, 'user', 'Customer', message);
        button.disabled = true;
        try {
            const data = await aiJson('/api/prompts/test', { method: 'POST', body: JSON.stringify({ message, instructions: fields.instructions.value }) });
            appendBubble(timeline, 'assistant', 'Prompt response', data.reply);
        } catch (error) { appendBubble(timeline, 'assistant', 'Test error', error.message); }
        finally { button.disabled = false; }
    };
    document.getElementById('runPromptTest').addEventListener('click', runTest);
    document.getElementById('promptTestInput').addEventListener('keydown', (event) => { if (event.key === 'Enter') runTest(); });
    document.getElementById('runPromptSuite').addEventListener('click', () => { setBadge(fields.status, 'Use the simulator to test this draft with your connected model', 'neutral'); document.getElementById('promptTestInput').focus(); });
    if (cards[0]) cards[0].click(); else load();
};

const initWorkflows = () => {
    const cards = [...document.querySelectorAll('.workflow-resource')];
    if (!document.getElementById('workflowName')) return;
    let currentId = null;
    let currentStatus = 'Draft';
    const status = document.getElementById('workflowStatus');
    const load = (workflow = {}) => {
        currentId = workflow.id || null; currentStatus = workflow.status || 'Draft';
        document.getElementById('workflowName').value = workflow.name || '';
        document.getElementById('workflowTrigger').value = workflow.trigger || 'Incoming WhatsApp message';
        document.getElementById('workflowRunMode').value = workflow.run_mode || 'Automatic';
        document.getElementById('workflowOwner').value = workflow.owner || 'Sales Team A';
        document.getElementById('workflowFailureAction').value = workflow.failure_action || 'Create support ticket';
        document.getElementById('workflowEditorTitle').textContent = workflow.name || 'New Workflow';
        setBadge(status, currentStatus, currentStatus === 'Live' ? 'good' : 'neutral');
    };
    cards.forEach((card) => { const workflow = JSON.parse(card.dataset.workflow); card.addEventListener('click', () => load(workflow)); });
    const save = async (publish = false) => {
        const button = publish ? document.getElementById('publishWorkflow') : document.getElementById('saveWorkflow');
        button.disabled = true;
        try {
            const data = await aiJson('/api/workflows', { method: 'POST', body: JSON.stringify({
                id: currentId, name: document.getElementById('workflowName').value.trim(),
                trigger: document.getElementById('workflowTrigger').value, owner: document.getElementById('workflowOwner').value,
                run_mode: document.getElementById('workflowRunMode').value, failure_action: document.getElementById('workflowFailureAction').value,
                status: publish ? 'Live' : 'Draft',
            }) });
            currentId = data.workflow.id; currentStatus = data.workflow.status;
            setBadge(status, publish ? 'Workflow published' : data.message, publish ? 'good' : 'neutral');
            if (!cards.some((card) => JSON.parse(card.dataset.workflow).id === currentId)) setTimeout(() => location.reload(), 350);
        } catch (error) { setBadge(status, error.message, 'warning'); }
        finally { button.disabled = false; }
    };
    document.getElementById('newWorkflow').addEventListener('click', () => load());
    document.getElementById('saveWorkflow').addEventListener('click', () => save(false));
    document.getElementById('publishWorkflow').addEventListener('click', () => save(true));
    document.querySelectorAll('.workflow-rule-toggle').forEach((toggle) => toggle.addEventListener('change', async () => {
        try { await aiJson(`/api/workflow-rules/${toggle.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: toggle.checked }) }); }
        catch (error) { toggle.checked = !toggle.checked; setBadge(status, error.message, 'warning'); }
    }));
    document.getElementById('exportWorkflows').addEventListener('click', () => {
        const rows = cards.map((card) => JSON.parse(card.dataset.workflow));
        const csv = ['Name,Trigger,Owner,Status,Runs,Success', ...rows.map((row) => [row.name, row.trigger, row.owner, row.status, row.runs, `${row.success}%`].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','))].join('\n');
        const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), download: 'workflows.csv' });
        link.click(); URL.revokeObjectURL(link.href);
    });
    if (cards[0]) cards[0].click(); else load();
};

const initKnowledgeManagement = () => {
    document.getElementById('addKnowledgeSource')?.addEventListener('click', () => document.getElementById('knowledgeDocumentImporter')?.scrollIntoView({ behavior: 'smooth' }));
    document.querySelectorAll('.knowledge-status').forEach((button) => button.addEventListener('click', async () => {
        const next = button.dataset.status === 'Published' ? 'Draft' : 'Published';
        try { await aiJson(`/api/knowledge-base/entries/${button.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ status: next }) }); button.dataset.status = next; setBadge(button, next, next === 'Published' ? 'good' : 'neutral'); }
        catch (error) { window.alert(error.message); }
    }));
    document.querySelectorAll('.delete-knowledge-entry').forEach((button) => button.addEventListener('click', async () => {
        if (!window.confirm('Delete this knowledge entry?')) return;
        try { await aiJson(`/api/knowledge-base/entries/${button.dataset.id}`, { method: 'DELETE' }); button.closest('.knowledge-entry-card').remove(); }
        catch (error) { window.alert(error.message); }
    }));
    document.getElementById('syncKnowledgeBase')?.addEventListener('click', async (event) => {
        const button = event.currentTarget; button.disabled = true;
        try { await aiJson('/api/knowledge-base/sync', { method: 'POST', body: JSON.stringify({ frequency: document.getElementById('kbSyncFrequency').value, approval_mode: document.getElementById('kbApprovalMode').value, notify_failures: document.getElementById('kbNotifyFailures').checked }) }); button.title = 'Synced just now'; }
        catch (error) { window.alert(error.message); }
        finally { button.disabled = false; }
    });
};

document.addEventListener('DOMContentLoaded', () => {
    initAiManagement(); initPromptBuilder(); initWorkflows(); initKnowledgeManagement();
});
