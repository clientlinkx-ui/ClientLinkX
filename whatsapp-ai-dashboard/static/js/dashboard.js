const fillProgressBars = () => {
    document.querySelectorAll('.progress-fill').forEach((fill) => {
        const progress = Number(fill.dataset.progress) || 0;
        fill.style.width = `${progress}%`;
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fillProgressBars);
} else {
    fillProgressBars();
}
