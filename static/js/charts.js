function initializeCharts(cpuData, memoryData, timestamps) {
    // CPU Chart
    new Chart(document.getElementById('cpuChart'), {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'CPU Usage',
                data: cpuData,
                borderColor: 'rgba(255, 99, 132, 1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, max: 100 }
            }
        }
    });

    // Memory Chart
    new Chart(document.getElementById('memoryChart'), {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'Memory Usage',
                data: memoryData,
                borderColor: 'rgba(255, 206, 86, 1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, max: 100 }
            }
        }
    });
}