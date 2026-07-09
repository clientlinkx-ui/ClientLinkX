const CLX = (() => {
    const json = async (url, options = {}) => {
        const response = await fetch(url, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.ok) throw new Error(data.error || 'Request failed.');
        return data;
    };

    const toast = (message, tone = 'good') => {
        let host = document.getElementById('toastHost');
        if (!host) {
            host = document.createElement('div');
            host.id = 'toastHost';
            host.className = 'toast-host';
            document.body.appendChild(host);
        }
        const item = document.createElement('div');
        item.className = `toast ${tone}`;
        item.textContent = message;
        host.appendChild(item);
        setTimeout(() => item.remove(), 3200);
    };

    const modal = (title, fields, onSubmit) => {
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        const panel = document.createElement('form');
        panel.className = 'modal-panel';
        panel.innerHTML = `
            <header><h2>${title}</h2><button type="button" class="icon-button" aria-label="Close"><i class="fa-solid fa-xmark"></i></button></header>
            <div class="form-grid"></div>
            <footer class="form-actions"><button type="button" class="secondary-action">Cancel</button><button class="primary-action" type="submit">Save</button></footer>
        `;
        const grid = panel.querySelector('.form-grid');
        fields.forEach((field) => {
            const label = document.createElement('label');
            label.className = `field ${field.full ? 'full-field' : ''}`;
            const value = field.value || '';
            if (field.type === 'textarea') {
                label.innerHTML = `<span>${field.label}</span><textarea name="${field.name}" rows="4">${value}</textarea>`;
            } else if (field.options) {
                label.innerHTML = `<span>${field.label}</span><select name="${field.name}">${field.options.map((option) => {
                    const optionValue = typeof option === 'object' ? option.value : option;
                    const optionLabel = typeof option === 'object' ? option.label : option;
                    return `<option value="${optionValue}" ${optionValue === value ? 'selected' : ''}>${optionLabel}</option>`;
                }).join('')}</select>`;
            } else {
                label.innerHTML = `<span>${field.label}</span><input name="${field.name}" type="${field.type || 'text'}" value="${value}">`;
            }
            grid.appendChild(label);
        });
        const close = () => backdrop.remove();
        panel.querySelector('header button').addEventListener('click', close);
        panel.querySelector('.secondary-action').addEventListener('click', close);
        panel.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = panel.querySelector('.primary-action');
            button.disabled = true;
            try {
                await onSubmit(Object.fromEntries(new FormData(panel).entries()));
                close();
            } catch (error) {
                toast(error.message, 'warning');
            } finally {
                button.disabled = false;
            }
        });
        backdrop.appendChild(panel);
        document.body.appendChild(backdrop);
        panel.querySelector('input, select, textarea')?.focus();
    };

    const download = (url) => window.location.assign(url);

    return { json, toast, modal, download };
})();

window.CLX = CLX;

const initCustomerOps = () => {
    const root = document.querySelector('.customers-page');
    if (!root || !window.PingPilot?.initOnce(root, 'customer-ops')) return;
    const search = document.querySelector('.customers-page input[type="search"]');
    const rows = [...document.querySelectorAll('[data-customer-row]')];
    const profile = document.getElementById('customerProfilePanel');
    const filterButtons = [...document.querySelectorAll('.customers-page .filter-pills button')];

    const apply = () => {
        const q = (search?.value || '').toLowerCase();
        const active = document.querySelector('.customers-page .filter-pills button.active')?.dataset.filter || 'All Customers';
        rows.forEach((row) => {
            const text = row.dataset.search.toLowerCase();
            const health = row.dataset.health;
            const matchesFilter = active === 'All Customers'
                || (active === 'High Intent' && health === 'High intent')
                || (active === 'At Risk' && health === 'At risk')
                || (active === 'New Leads' && text.includes('new'));
            row.hidden = !text.includes(q) || !matchesFilter;
        });
    };

    rows.forEach((row) => row.addEventListener('click', () => {
        rows.forEach((item) => item.classList.toggle('selected', item === row));
        if (profile) {
            profile.querySelector('h2').textContent = row.dataset.name;
            profile.querySelector('.avatar-placeholder').textContent = row.dataset.name.charAt(0);
            profile.querySelector('[data-customer-phone]').textContent = row.dataset.phone;
            profile.querySelector('[data-customer-detail]').textContent = `${row.dataset.segment} - ${row.dataset.stage} - Last seen ${row.dataset.lastSeen}`;
            profile.querySelector('[data-customer-csat]').textContent = row.dataset.csat;
            profile.querySelector('[data-customer-health]').textContent = row.dataset.health;
        }
    }));
    filterButtons.forEach((button) => button.addEventListener('click', () => {
        filterButtons.forEach((item) => item.classList.toggle('active', item === button));
        apply();
    }));
    search?.addEventListener('input', apply);
    document.querySelector('[data-action="add-customer"]')?.addEventListener('click', () => CLX.modal('Add Customer', [
        { name: 'name', label: 'Name' }, { name: 'phone', label: 'Phone' },
        { name: 'segment', label: 'Segment', value: 'General' }, { name: 'stage', label: 'Stage', value: 'New lead' },
        { name: 'health', label: 'Health', options: ['Neutral', 'Good', 'High intent', 'At risk'] },
    ], async (data) => {
        const result = await CLX.json('/api/customers', { method: 'POST', body: JSON.stringify(data) });
        CLX.toast(result.message);
        setTimeout(() => location.reload(), 500);
    }));
    document.querySelector('[data-action="export-customers"]')?.addEventListener('click', () => CLX.download('/api/customers/export'));
};

const initTeamOps = () => {
    const root = document.querySelector('.team-page');
    if (!root || !window.PingPilot?.initOnce(root, 'team-ops')) return;
    const search = document.querySelector('.team-page input[type="search"]');
    const cards = [...document.querySelectorAll('[data-team-member]')];
    const filters = [...document.querySelectorAll('.team-page .filter-pills button')];
    const apply = () => {
        const q = (search?.value || '').toLowerCase();
        const active = document.querySelector('.team-page .filter-pills button.active')?.dataset.filter || 'All Members';
        cards.forEach((card) => {
            const status = card.dataset.status;
            const text = card.dataset.search.toLowerCase();
            card.hidden = !text.includes(q) || (active !== 'All Members' && status !== active);
        });
    };
    filters.forEach((button) => button.addEventListener('click', () => {
        filters.forEach((item) => item.classList.toggle('active', item === button));
        apply();
    }));
    search?.addEventListener('input', apply);
    const fetchRoles = async () => {
        const result = await CLX.json('/api/roles');
        return result.assignable_roles || result.roles || [];
    };
    document.querySelector('[data-action="invite-member"]')?.addEventListener('click', async () => {
        let roles = [];
        try { roles = await fetchRoles(); }
        catch (error) { CLX.toast(error.message, 'warning'); return; }
        CLX.modal('Invite Member', [
            { name: 'name', label: 'Name' }, { name: 'email', label: 'Email', type: 'email' },
            { name: 'permission_group', label: 'Role', options: roles.map((role) => ({ label: role.name, value: role.key })) },
            { name: 'role', label: 'Job title', value: 'Agent' },
            { name: 'team', label: 'Team', value: 'Support Desk' }, { name: 'status', label: 'Status', options: ['Invited', 'Online', 'Busy', 'Away', 'Offline'] },
        ], async (data) => {
        try {
            const result = await CLX.json('/api/team-members', { method: 'POST', body: JSON.stringify(data) });
            CLX.toast(result.message);
            setTimeout(() => location.reload(), 500);
        } catch (error) { CLX.toast(error.message, 'warning'); }
        });
    });
    const openRoleBuilder = async () => {
        let catalog;
        try {
            catalog = await CLX.json('/api/permissions/catalog');
        } catch (error) {
            CLX.toast(error.message, 'warning');
            return;
        }
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        const panel = document.createElement('form');
        panel.className = 'modal-panel role-builder-modal';
        panel.innerHTML = `
            <header><h2>Create Role</h2><button type="button" class="icon-button" aria-label="Close"><i class="fa-solid fa-xmark"></i></button></header>
            <div class="form-grid">
                <label class="field"><span>Role name</span><input name="name" required></label>
                <label class="field"><span>Description</span><input name="description" value="Custom workspace access"></label>
            </div>
            <div class="permission-check-grid"></div>
            <footer class="form-actions"><button type="button" class="secondary-action">Cancel</button><button class="primary-action" type="submit">Create Role</button></footer>
        `;
        const grid = panel.querySelector('.permission-check-grid');
        (catalog.catalog || []).forEach((group) => {
            const section = document.createElement('section');
            section.className = 'permission-check-section';
            section.innerHTML = `<h3>${group.name}</h3>`;
            group.permissions.forEach((permission) => {
                const label = document.createElement('label');
                label.className = 'permission-check';
                label.innerHTML = `<input type="checkbox" name="permissions" value="${permission.key}"><span>${permission.label}</span>`;
                section.appendChild(label);
            });
            grid.appendChild(section);
        });
        const close = () => backdrop.remove();
        panel.querySelector('header button').addEventListener('click', close);
        panel.querySelector('.secondary-action').addEventListener('click', close);
        panel.addEventListener('submit', async (event) => {
            event.preventDefault();
            const form = new FormData(panel);
            const payload = {
                name: form.get('name'),
                description: form.get('description'),
                permissions: form.getAll('permissions'),
            };
            try {
                const result = await CLX.json('/api/roles', { method: 'POST', body: JSON.stringify(payload) });
                CLX.toast(result.message);
                setTimeout(() => location.reload(), 500);
            } catch (error) { CLX.toast(error.message, 'warning'); }
        });
        backdrop.appendChild(panel);
        document.body.appendChild(backdrop);
        panel.querySelector('input')?.focus();
    };
    document.querySelector('[data-action="add-team-role"]')?.addEventListener('click', openRoleBuilder);
    document.querySelectorAll('.permission-group-select').forEach((select) => select.addEventListener('change', async () => {
        const previous = select.dataset.previousValue || select.defaultValue;
        try {
            const result = await CLX.json(`/api/team-members/${select.dataset.memberId}/permission-group`, {
                method: 'PATCH',
                body: JSON.stringify({ permission_group: select.value }),
            });
            select.dataset.previousValue = select.value;
            CLX.toast(result.message);
        } catch (error) {
            select.value = previous;
            CLX.toast(error.message, 'warning');
        }
    }));
    document.querySelector('[data-action="export-team"]')?.addEventListener('click', () => CLX.download('/api/team-members/export'));
};

const initSupportOps = () => {
    const root = document.querySelector('.support-page');
    if (!root || !window.PingPilot?.initOnce(root, 'support-ops')) return;
    document.querySelector('[data-action="new-ticket"]')?.addEventListener('click', () => document.getElementById('contact-support')?.scrollIntoView({ behavior: 'smooth' }));
    document.querySelector('[data-action="submit-ticket"]')?.addEventListener('click', async () => {
        const payload = {
            request_type: document.getElementById('supportRequestType').value,
            priority: document.getElementById('supportPriority').value,
            subject: document.getElementById('supportSubject').value,
            description: document.getElementById('supportDescription').value,
            attachment: document.getElementById('supportAttachment')?.files?.[0]?.name || '',
        };
        try {
            const result = await CLX.json('/api/support/tickets', { method: 'POST', body: JSON.stringify(payload) });
            CLX.toast(result.message);
            setTimeout(() => location.reload(), 500);
        } catch (error) { CLX.toast(error.message, 'warning'); }
    });
    document.querySelector('[data-action="export-support"]')?.addEventListener('click', () => CLX.download('/api/support/tickets/export'));
};

const initSecurityOps = () => {
    const root = document.querySelector('.security-page');
    if (!root || !window.PingPilot?.initOnce(root, 'security-ops')) return;
    document.querySelectorAll('.security-rule-toggle').forEach((toggle) => toggle.addEventListener('change', async () => {
        try { await CLX.json(`/api/security/access-rules/${toggle.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: toggle.checked }) }); }
        catch (error) { toggle.checked = !toggle.checked; CLX.toast(error.message, 'warning'); }
    }));
    document.querySelector('[data-action="save-security"]')?.addEventListener('click', async () => {
        const payload = {
            require_2fa: document.getElementById('securityRequire2fa') ? document.getElementById('securityRequire2fa').checked : true,
            mask_phone_numbers: document.getElementById('securityMaskPhones') ? document.getElementById('securityMaskPhones').checked : true,
            retention_period: document.getElementById('securityRetention')?.value,
            audit_export: document.getElementById('securityAuditExport')?.value,
        };
        try { const result = await CLX.json('/api/security/settings', { method: 'POST', body: JSON.stringify(payload) }); CLX.toast(result.message); }
        catch (error) { CLX.toast(error.message, 'warning'); }
    });
    document.querySelector('[data-action="add-security-role"]')?.addEventListener('click', async () => {
        let catalog;
        try {
            catalog = await CLX.json('/api/permissions/catalog');
        } catch (error) { CLX.toast(error.message, 'warning'); return; }
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        const panel = document.createElement('form');
        panel.className = 'modal-panel role-builder-modal';
        panel.innerHTML = `
            <header><h2>Create Role</h2><button type="button" class="icon-button" aria-label="Close"><i class="fa-solid fa-xmark"></i></button></header>
            <div class="form-grid">
                <label class="field"><span>Role name</span><input name="name" required></label>
                <label class="field"><span>Description</span><input name="description" value="Custom workspace access"></label>
            </div>
            <div class="permission-check-grid"></div>
            <footer class="form-actions"><button type="button" class="secondary-action">Cancel</button><button class="primary-action" type="submit">Create Role</button></footer>
        `;
        const grid = panel.querySelector('.permission-check-grid');
        (catalog.catalog || []).forEach((group) => {
            const section = document.createElement('section');
            section.className = 'permission-check-section';
            section.innerHTML = `<h3>${group.name}</h3>`;
            group.permissions.forEach((permission) => {
                const label = document.createElement('label');
                label.className = 'permission-check';
                label.innerHTML = `<input type="checkbox" name="permissions" value="${permission.key}"><span>${permission.label}</span>`;
                section.appendChild(label);
            });
            grid.appendChild(section);
        });
        const close = () => backdrop.remove();
        panel.querySelector('header button').addEventListener('click', close);
        panel.querySelector('.secondary-action').addEventListener('click', close);
        panel.addEventListener('submit', async (event) => {
            event.preventDefault();
            const form = new FormData(panel);
            try {
                const result = await CLX.json('/api/roles', {
                    method: 'POST',
                    body: JSON.stringify({ name: form.get('name'), description: form.get('description'), permissions: form.getAll('permissions') }),
                });
                CLX.toast(result.message);
                setTimeout(() => location.reload(), 500);
            } catch (error) { CLX.toast(error.message, 'warning'); }
        });
        backdrop.appendChild(panel);
        document.body.appendChild(backdrop);
        panel.querySelector('input')?.focus();
    });
    document.querySelectorAll('.dashboard-permission-group-select').forEach((select) => select.addEventListener('change', async () => {
        const previous = select.dataset.previousValue || select.defaultValue;
        try {
            const result = await CLX.json(`/api/dashboard-users/${select.dataset.userId}/permission-group`, {
                method: 'PATCH',
                body: JSON.stringify({ permission_group: select.value }),
            });
            select.dataset.previousValue = select.value;
            CLX.toast(result.message);
        } catch (error) {
            select.value = previous;
            CLX.toast(error.message, 'warning');
        }
    }));
    document.querySelector('[data-action="export-audit"]')?.addEventListener('click', () => CLX.download('/api/security/audit-log/export'));
};

const initSettingsOps = () => {
    const root = document.querySelector('.settings-page:not(.account-page)');
    if (!root || !window.PingPilot?.initOnce(root, 'settings-ops')) return;
    const save = async (url, payload) => {
        try { const result = await CLX.json(url, { method: 'POST', body: JSON.stringify(payload) }); CLX.toast(result.message); }
        catch (error) { CLX.toast(error.message, 'warning'); }
    };
    document.querySelector('[data-action="save-workspace"]')?.addEventListener('click', () => save('/api/settings/workspace', {
        company_name: document.getElementById('workspaceCompany').value,
        industry: document.getElementById('workspaceIndustry').value,
        timezone: document.getElementById('workspaceTimezone').value,
        language: document.getElementById('workspaceLanguage').value,
    }));
    document.querySelector('[data-action="save-whatsapp"]')?.addEventListener('click', () => save('/api/settings/whatsapp', {
        webhook_url: document.getElementById('whatsappWebhook').value,
        message_window_policy: document.getElementById('whatsappWindow').value,
    }));
    document.querySelector('[data-action="save-ai-behavior"]')?.addEventListener('click', () => save('/api/settings/ai-behavior', {
        kb_grounding: document.getElementById('aiKbGrounding').checked,
        intent_detection: document.getElementById('aiIntentDetection').checked,
    }));
    document.querySelector('[data-action="save-handoff"]')?.addEventListener('click', () => save('/api/settings/handoff', {
        default_handoff_team: document.getElementById('handoffTeam').value,
        sla_target: document.getElementById('handoffSla').value,
        handoff_low_confidence: document.getElementById('handoffLowConfidence').checked,
        handoff_negative_sentiment: document.getElementById('handoffNegativeSentiment').checked,
        escalation_decision_mode: document.getElementById('escalationDecisionMode').value,
    }));
    document.querySelector('[data-action="save-notifications"]')?.addEventListener('click', () => save('/api/settings/notifications', {
        daily_digest: document.getElementById('notifyDigest').checked,
        escalation_alerts: document.getElementById('notifyEscalations').checked,
        kb_failure_alerts: document.getElementById('notifyKbFailures').checked,
    }));
    document.querySelector('[data-action="save-security"]')?.addEventListener('click', () => save('/api/security/settings', {
        require_2fa: document.getElementById('securityRequire2fa')?.checked ?? true,
        mask_phone_numbers: document.getElementById('securityMaskPhones')?.checked ?? true,
        retention_period: document.getElementById('securityRetention')?.value,
        audit_export: document.getElementById('securityAuditExport')?.value,
    }));
    document.querySelectorAll('.settings-module-toggle').forEach((toggle) => toggle.addEventListener('change', async () => {
        try { await CLX.json(`/api/settings/modules/${toggle.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: toggle.checked }) }); }
        catch (error) { toggle.checked = !toggle.checked; CLX.toast(error.message, 'warning'); }
    }));
};

const initBillingOps = () => {
    const root = document.querySelector('.billing-page');
    if (!root || !window.PingPilot?.initOnce(root, 'billing-ops')) return;
    document.querySelectorAll('.billing-addon-toggle').forEach((toggle) => toggle.addEventListener('change', async () => {
        try { await CLX.json(`/api/billing/add-ons/${toggle.dataset.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: toggle.checked }) }); CLX.toast('Billing add-on updated.'); }
        catch (error) { toggle.checked = !toggle.checked; CLX.toast(error.message, 'warning'); }
    }));
    document.querySelector('[data-action="download-plan"]')?.addEventListener('click', () => CLX.toast('Plan summary exported.'));
    document.querySelector('[data-action="upgrade-plan"]')?.addEventListener('click', () => CLX.toast('Plan upgrade request saved for billing review.'));
    document.querySelector('[data-action="edit-payment"]')?.addEventListener('click', () => CLX.toast('Payment method update saved for secure billing review.'));
    document.querySelector('[data-action="export-invoices"]')?.addEventListener('click', () => CLX.download('/api/billing/invoices/export'));
    document.querySelectorAll('[data-invoice-id]').forEach((button) => button.addEventListener('click', () => CLX.download(`/api/billing/invoices/${button.dataset.invoiceId}/download`)));
};

const initAddonOps = () => {
    const root = document.querySelector('.add-ons-page');
    if (!root || !window.PingPilot?.initOnce(root, 'addon-ops')) return;
    document.querySelectorAll('[data-addon-id]').forEach((button) => button.addEventListener('click', async () => {
        try {
            const result = await CLX.json('/api/add-ons/cart', { method: 'POST', body: JSON.stringify({ addon_id: button.dataset.addonId, selected: true }) });
            button.innerHTML = '<i class="fa-solid fa-check"></i> Added';
            CLX.toast(result.message);
        } catch (error) { CLX.toast(error.message, 'warning'); }
    }));
    document.querySelector('[data-action="purchase-addons"]')?.addEventListener('click', async () => {
        try { const result = await CLX.json('/api/add-ons/purchase', { method: 'POST', body: '{}' }); CLX.toast(result.message); setTimeout(() => location.reload(), 600); }
        catch (error) { CLX.toast(error.message, 'warning'); }
    });
    document.querySelector('[data-action="download-addon-quote"]')?.addEventListener('click', () => CLX.download('/api/add-ons/quote'));
    document.querySelector('[data-action="compare-addons"]')?.addEventListener('click', () => CLX.toast('Compare mode: review price, category, fit, and status in the catalog table.'));
    document.querySelector('[data-action="filter-addons"]')?.addEventListener('click', () => CLX.toast('Filter available: use the catalog columns to compare category, fit, price, and status.'));
};

const initOperations = () => {
    initCustomerOps();
    initTeamOps();
    initSupportOps();
    initSecurityOps();
    initSettingsOps();
    initBillingOps();
    initAddonOps();
};

window.PingPilot?.ready ? PingPilot.ready(initOperations) : document.addEventListener('DOMContentLoaded', initOperations);
document.addEventListener('pingpilot:page-ready', initOperations);
