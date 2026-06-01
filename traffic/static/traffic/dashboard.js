async function loadChart() {
    const useReal = document.getElementById("realPricesToggle")?.checked ? "true" : "false";
    const response = await fetch(`/chart-data/?real=${useReal}`);
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

const MONTH_NAMES = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
];

const monthlyCharts = {};

async function loadMonthlyCharts() {
    const response = await fetch("/chart-data/by-month/");
    const json = await response.json();

    for (let month = 1; month <= 12; month++) {
        const entries = json.data[month] || [];
        const labels        = entries.map(r => r.year);
        const accidents     = entries.map(r => r.accidents_total);
        const diesel        = entries.map(r => r.avg_diesel);
        const avgPetrol     = entries.map(r => r.avg_petrol);

        const ctx = document.getElementById(`monthChart${month}`).getContext("2d");

        if (monthlyCharts[month] instanceof Chart) {
            monthlyCharts[month].destroy();
        }

        monthlyCharts[month] = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Wypadki",
                        data: accidents,
                        borderColor: "rgb(255, 99, 132)",
                        yAxisID: "y",
                        tension: 0.3,
                    },
                    {
                        label: "Śr. cena ON (zł)",
                        data: diesel,
                        borderColor: "rgb(54, 162, 235)",
                        yAxisID: "y2",
                        tension: 0.3,
                    },
                    {
                        label: "Śr. cena E95 (zł)",
                        data: avgPetrol,
                        borderColor: "rgb(75, 192, 192)",
                        yAxisID: "y2",
                        tension: 0.3,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "top" },
                    title: { display: true, text: MONTH_NAMES[month - 1] },
                },
                interaction: { mode: "index", intersect: false },
                scales: {
                    y:  { position: "left",  title: { display: true, text: "Wypadki" } },
                    y2: { position: "right", title: { display: true, text: "Cena ON (zł)" }, grid: { drawOnChartArea: false } }
                }
            }
        });
    }
}

async function loadCorrelationTable() {
    const response = await fetch("/correlation/");
    const json = await response.json();

    const tbody = document.getElementById("correlation-body");
    tbody.innerHTML = "";

    for (const row of json.data) {
        const significant = row.significant === true || row.significant === "True";
        const r = row.correlation;

        let bgColor = "#f0f0f0";
        if (significant && r < 0) bgColor = "#d4edda";
        if (significant && r > 0) bgColor = "#f8d7da";

        const tr = document.createElement("tr");
        tr.style.backgroundColor = bgColor;
        tr.innerHTML = `
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${row.month_name}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${r.toFixed(3)}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${row.p_value.toFixed(4)}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${row.n}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${significant ? "Tak" : "Nie"}</td>
        `;
        tbody.appendChild(tr);
    }
}

function sync_inflation(startYear, endYear) {
    const url = `/gus/inflation/?start=${startYear}&end=${endYear}`;

    fetch(url)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Wystąpił nieoczekiwany błąd serwera.');
                });
            }
            return response.json();
        })
        .then(jsonData => {
            console.log("Zapisano pomyślnie:", jsonData.data);
        })
        .catch(error => {
            console.error("Błąd synchronizacji:", error.message);
        });
}