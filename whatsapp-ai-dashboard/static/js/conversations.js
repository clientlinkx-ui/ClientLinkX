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
        row.addEventListener('click', () => {
            rows.forEach((item) => item.classList.toggle('active', item === row));
        });
    });

    searchInput?.addEventListener('input', applyFilters);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initConversationFilters);
} else {
    initConversationFilters();
}
