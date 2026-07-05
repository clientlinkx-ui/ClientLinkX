const chartDefaults = () => {
    if (!window.Chart) {
        return;
    }

    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.color = '#64748b';
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
};

const renderTrafficChart = () => {
    const canvas = document.getElementById('trafficChart');

    if (!canvas || !window.Chart) {
        return;
    }

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [
                {
                    label: 'AI handled',
                    data: [1840, 2140, 2380, 2210, 2690, 2860, 3120],
                    borderColor: '#128c7e',
                    backgroundColor: 'rgba(18, 140, 126, 0.12)',
                    fill: true,
                    tension: 0.38,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                },
                {
                    label: 'Human escalated',
                    data: [210, 248, 224, 276, 240, 196, 178],
                    borderColor: '#d97706',
                    backgroundColor: 'rgba(217, 119, 6, 0.08)',
                    fill: true,
                    tension: 0.38,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'bottom',
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                    },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `${value / 1000}k`,
                    },
                    grid: {
                        color: '#eef2f6',
                    },
                },
            },
        },
    });
};

const renderStatusChart = () => {
    const canvas = document.getElementById('statusChart');

    if (!canvas || !window.Chart) {
        return;
    }

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Resolved by AI', 'Waiting', 'Escalated', 'Abandoned'],
            datasets: [
                {
                    data: [68, 14, 12, 6],
                    backgroundColor: ['#128c7e', '#2563eb', '#d97706', '#dc2626'],
                    borderWidth: 0,
                    hoverOffset: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: {
                    position: 'bottom',
                },
            },
        },
    });
};

const renderAnalyticsVolumeChart = () => {
    const canvas = document.getElementById('analyticsVolumeChart');

    if (!canvas || !window.Chart) {
        return;
    }

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            datasets: [
                {
                    label: 'Conversations',
                    data: [3820, 4210, 4890, 5500],
                    backgroundColor: '#128c7e',
                    borderRadius: 6,
                },
                {
                    label: 'Escalations',
                    data: [268, 244, 236, 212],
                    backgroundColor: '#d97706',
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#eef2f6',
                    },
                },
            },
        },
    });
};

const renderAnalyticsIntentChart = () => {
    const canvas = document.getElementById('analyticsIntentChart');

    if (!canvas || !window.Chart) {
        return;
    }

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Orders', 'Admissions', 'Appointments', 'Sales', 'Refunds'],
            datasets: [
                {
                    data: [32, 21, 16, 14, 8],
                    backgroundColor: ['#128c7e', '#2563eb', '#16a34a', '#d97706', '#dc2626'],
                    borderWidth: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '64%',
            plugins: {
                legend: {
                    position: 'bottom',
                },
            },
        },
    });
};

const renderSatisfactionChart = () => {
    const canvas = document.getElementById('satisfactionChart');

    if (!canvas || !window.Chart) {
        return;
    }

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [
                {
                    label: 'CSAT',
                    data: [91, 92, 93, 92, 94, 95, 94],
                    borderColor: '#16a34a',
                    backgroundColor: 'rgba(22, 163, 74, 0.12)',
                    fill: true,
                    tension: 0.38,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                    },
                },
                y: {
                    min: 80,
                    max: 100,
                    ticks: {
                        callback: (value) => `${value}%`,
                    },
                    grid: {
                        color: '#eef2f6',
                    },
                },
            },
        },
    });
};

const initCharts = () => {
    chartDefaults();
    renderTrafficChart();
    renderStatusChart();
    renderAnalyticsVolumeChart();
    renderAnalyticsIntentChart();
    renderSatisfactionChart();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCharts);
} else {
    initCharts();
}
