const onboardingRoot = document.querySelector('[data-onboarding]');
const statusNode = document.getElementById('onboardingStatus');

let onboardingSession = null;
let selectedPlan = 'growth';
let billingCycle = 'monthly';

const stepOrder = ['account', 'company', 'email', 'whatsapp', 'plan', 'review'];

const json = async (url, options = {}) => {
    const response = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || 'Request failed.');
    return data;
};

const setStatus = (message, tone = 'neutral') => {
    if (!statusNode) return;
    statusNode.textContent = message;
    statusNode.dataset.tone = tone;
};

const showStep = (step) => {
    document.querySelectorAll('.onboarding-step').forEach((panel) => {
        panel.classList.toggle('active', panel.dataset.step === step);
    });
    document.querySelectorAll('[data-step-dot]').forEach((item) => {
        const itemIndex = stepOrder.indexOf(item.dataset.stepDot);
        const stepIndex = stepOrder.indexOf(step);
        item.classList.toggle('active', item.dataset.stepDot === step);
        item.classList.toggle('complete', itemIndex < stepIndex);
    });
    if (step === 'review') renderReview();
};

const uiStep = (step) => ({
    verify_email: 'email',
    verify_whatsapp: 'whatsapp',
    complete: 'review',
}[step] || step || 'account');

const updateVerificationBadges = () => {
    const emailBadge = document.getElementById('emailVerifiedBadge');
    const whatsappBadge = document.getElementById('whatsappVerifiedBadge');
    if (emailBadge) {
        emailBadge.textContent = onboardingSession?.email_verified ? 'Verified' : 'Not verified';
        emailBadge.className = `settings-badge ${onboardingSession?.email_verified ? 'good' : 'neutral-badge'}`;
    }
    if (whatsappBadge) {
        whatsappBadge.textContent = onboardingSession?.whatsapp_verified ? 'Verified' : 'Not verified';
        whatsappBadge.className = `settings-badge ${onboardingSession?.whatsapp_verified ? 'good' : 'neutral-badge'}`;
    }
};

const renderReview = () => {
    const grid = document.getElementById('reviewGrid');
    if (!grid || !onboardingSession) return;
    const plan = onboardingSession.selected_plan_detail || {};
    const rows = [
        ['Company', onboardingSession.company_name],
        ['Business type', onboardingSession.industry],
        ['Workspace email', onboardingSession.company_email],
        ['WhatsApp number', onboardingSession.company_phone],
        ['Email verification', onboardingSession.email_verified ? 'Verified' : 'Pending'],
        ['WhatsApp verification', onboardingSession.whatsapp_verified ? 'Verified' : 'Pending'],
        ['Plan', `${plan.name || onboardingSession.selected_plan} · ${onboardingSession.billing_cycle}`],
    ];
    grid.innerHTML = rows.map(([label, value]) => `
        <div class="review-item">
            <span>${label}</span>
            <strong>${value || 'Not set'}</strong>
        </div>
    `).join('');
};

const applySession = (session) => {
    onboardingSession = session;
    selectedPlan = session?.selected_plan || selectedPlan;
    billingCycle = session?.billing_cycle || billingCycle;
    updateVerificationBadges();
    document.querySelectorAll('[data-plan]').forEach((button) => button.classList.toggle('active', button.dataset.plan === selectedPlan));
    document.querySelectorAll('[data-cycle]').forEach((button) => button.classList.toggle('active', button.dataset.cycle === billingCycle));
    document.querySelectorAll('.plan-choice strong').forEach((price) => {
        price.textContent = price.dataset[billingCycle] || price.textContent;
    });
};

const payloadFromForm = (form) => Object.fromEntries(new FormData(form).entries());

const requireVerified = (channel) => {
    if (channel === 'email' && !onboardingSession?.email_verified) throw new Error('Verify company email before continuing.');
    if (channel === 'whatsapp' && !onboardingSession?.whatsapp_verified) throw new Error('Verify WhatsApp before continuing.');
};

document.querySelector('[data-step="account"]')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
        const result = await json('/api/onboarding/account', { method: 'POST', body: JSON.stringify(payloadFromForm(event.currentTarget)) });
        applySession(result.session);
        setStatus(result.message, 'good');
        showStep('company');
    } catch (error) { setStatus(error.message, 'warning'); }
});

document.querySelector('[data-step="company"]')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
        const result = await json('/api/onboarding/company', { method: 'POST', body: JSON.stringify(payloadFromForm(event.currentTarget)) });
        applySession(result.session);
        setStatus(result.message, 'good');
        showStep('email');
    } catch (error) { setStatus(error.message, 'warning'); }
});

document.querySelectorAll('[data-back]').forEach((button) => button.addEventListener('click', () => showStep(button.dataset.back)));

document.querySelectorAll('[data-next]').forEach((button) => button.addEventListener('click', () => {
    try {
        if (button.dataset.next === 'whatsapp') requireVerified('email');
        if (button.dataset.next === 'plan') requireVerified('whatsapp');
        showStep(button.dataset.next);
    } catch (error) { setStatus(error.message, 'warning'); }
}));

document.querySelectorAll('[data-send-code]').forEach((button) => button.addEventListener('click', async () => {
    const channel = button.dataset.sendCode;
    try {
        button.disabled = true;
        const result = await json(`/api/onboarding/verify/${channel}/send`, { method: 'POST', body: JSON.stringify({}) });
        applySession(result.session);
        const devNode = document.getElementById(`${channel}DevCode`);
        if (devNode && result.test_code) {
            devNode.hidden = false;
            devNode.textContent = `Development code: ${result.test_code}`;
        }
        setStatus(result.dev_mode ? `${result.message} Development code shown below.` : result.message, 'good');
    } catch (error) {
        setStatus(error.message, 'warning');
    } finally {
        button.disabled = false;
    }
}));

document.querySelectorAll('[data-check-code]').forEach((button) => button.addEventListener('click', async () => {
    const channel = button.dataset.checkCode;
    const input = document.getElementById(`${channel}Code`);
    try {
        const result = await json(`/api/onboarding/verify/${channel}/check`, {
            method: 'POST',
            body: JSON.stringify({ code: input?.value || '' }),
        });
        applySession(result.session);
        setStatus(result.message, 'good');
    } catch (error) { setStatus(error.message, 'warning'); }
}));

document.querySelectorAll('[data-cycle]').forEach((button) => button.addEventListener('click', () => {
    billingCycle = button.dataset.cycle;
    applySession({ ...onboardingSession, billing_cycle: billingCycle, selected_plan: selectedPlan });
}));

document.querySelectorAll('[data-plan]').forEach((button) => button.addEventListener('click', () => {
    selectedPlan = button.dataset.plan;
    applySession({ ...onboardingSession, billing_cycle: billingCycle, selected_plan: selectedPlan });
}));

document.querySelector('[data-save-plan]')?.addEventListener('click', async () => {
    try {
        requireVerified('email');
        requireVerified('whatsapp');
        const result = await json('/api/onboarding/plan', {
            method: 'POST',
            body: JSON.stringify({ plan: selectedPlan, billing_cycle: billingCycle }),
        });
        applySession(result.session);
        setStatus(result.message, 'good');
        showStep('review');
    } catch (error) { setStatus(error.message, 'warning'); }
});

document.querySelector('[data-complete-onboarding]')?.addEventListener('click', async () => {
    try {
        const result = await json('/api/onboarding/complete', { method: 'POST', body: JSON.stringify({}) });
        setStatus(result.message, 'good');
        window.location.assign(result.redirect_url || '/');
    } catch (error) { setStatus(error.message, 'warning'); }
});

(async () => {
    if (!onboardingRoot) return;
    try {
        const result = await json('/api/onboarding/session');
        applySession(result.session);
        showStep(uiStep(result.session?.current_step));
    } catch (error) {
        setStatus(error.message, 'warning');
    }
})();
