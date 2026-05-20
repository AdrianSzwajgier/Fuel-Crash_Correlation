async function loadChart() {
    const response = await fetch("/chart-data/");
    const json = await response.json();

    const labels        = json.data.map(r => r.label);
    const accidents     = json.data.map(r => r.accidents_total);
    const avgDiesel     = json.data.map(r => r.avg_diesel);
    const avgPetrol     = json.data.map(r => r.avg_petrol);

    const ctx = document.getElementById("accidentsChart").getContext("2d");

    if (window.accidentsChart instanceof Chart) {
        window.accidentsChart.destroy();
    }

    window.accidentsChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Wypadki ogółem",
                    data: accidents,
                    borderColor: "rgb(255, 99, 132)",
                    backgroundColor: "rgba(255, 99, 132, 0.1)",
                    tension: 0.3,
                    fill: true,
                    yAxisID: "y",
                },
                {
                    label: "Śr. cena ON (zł)",
                    data: avgDiesel,
                    borderColor: "rgb(54, 162, 235)",
                    backgroundColor: "transparent",
                    tension: 0.3,
                    yAxisID: "y2",
                },
                {
                    label: "Śr. cena E95 (zł)",
                    data: avgPetrol,
                    borderColor: "rgb(75, 192, 192)",
                    backgroundColor: "transparent",
                    tension: 0.3,
                    yAxisID: "y2",
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: "index",        // tooltip pokazuje wszystkie serie naraz
                intersect: false,
            },
            plugins: {
                legend: { position: "top" },
            },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 24 }
                },
                y: {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Liczba wypadków" },
                    beginAtZero: false,
                },
                y2: {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Cena paliwa (zł)" },
                    beginAtZero: false,
                    grid: { drawOnChartArea: false },
                }
            }
        }
    });
}