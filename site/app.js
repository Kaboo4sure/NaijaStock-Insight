let stockData = [];
let signalData = [];
let metadata = {};
let latestPrices = [];
const mobileViewport = window.matchMedia("(max-width: 700px)");
let previousMobileLayout = mobileViewport.matches;

const elements = {
    latestDate: document.getElementById("latestDate"),
    companyCount: document.getElementById("companyCount"),
    recordCount: document.getElementById("recordCount"),
    buySignalCount: document.getElementById("buySignalCount"),
    lastUpdated: document.getElementById("lastUpdated"),
    companySelect: document.getElementById("companySelect"),
    chartType: document.getElementById("chartType"),
    changePeriod: document.getElementById("changePeriod"),
    changeHeader: document.getElementById("changeHeader"),
    chartTitle: document.getElementById("chartTitle"),
    stockSearch: document.getElementById("stockSearch"),
    stockTableBody: document.getElementById("stockTableBody"),
    signalTableBody: document.getElementById("signalTableBody"),
    downloadSignals: document.getElementById("downloadSignals"),
    errorPanel: document.getElementById("errorPanel"),
    errorMessage: document.getElementById("errorMessage")
};

async function loadDashboard() {
    try {
        const cacheBuster = `?version=${Date.now()}`;

        const [stocksResponse, signalsResponse, metadataResponse] =
            await Promise.all([
                fetch(`data/stocks.json${cacheBuster}`),
                fetch(`data/signals.json${cacheBuster}`),
                fetch(`data/metadata.json${cacheBuster}`)
            ]);

        if (
            !stocksResponse.ok ||
            !signalsResponse.ok ||
            !metadataResponse.ok
        ) {
            throw new Error("One or more website data files could not be loaded.");
        }

        stockData = await stocksResponse.json();
        signalData = await signalsResponse.json();
        metadata = await metadataResponse.json();

        if (!stockData.length) {
            throw new Error("The stock-data file contains no records.");
        }

        populateCompanySelector();
        updateMetrics();
        renderChart();
        renderStockTable();
        renderSignalTable();
        attachEventListeners();
    } catch (error) {
        showError(error.message);
        console.error(error);
    }
}

function normalizeDate(value) {
    if (!value) return "";
    return String(value).substring(0, 10);
}

function numberValue(value) {
    const converted = Number(value);
    return Number.isFinite(converted) ? converted : 0;
}

function formatPrice(value) {
    return numberValue(value).toLocaleString("en-NG", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatVolume(value) {
    return numberValue(value).toLocaleString("en-NG");
}

function formatIndicator(value) {
    const converted = Number(value);
    return Number.isFinite(converted) ? converted.toFixed(2) : "—";
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function populateCompanySelector() {
    const companiesByTicker = new Map();

    stockData.forEach((record) => {
        companiesByTicker.set(
            record.ticker,
            record.company_name || record.ticker
        );
    });

    const companies = [...companiesByTicker.entries()].sort((a, b) =>
        a[1].localeCompare(b[1])
    );

    elements.companySelect.innerHTML = companies
        .map(
            ([ticker, company]) =>
                `<option value="${escapeHtml(ticker)}">
                    ${escapeHtml(company)} (${escapeHtml(ticker)})
                </option>`
        )
        .join("");
}

function updateMetrics() {
    const dates = stockData
        .map((record) => normalizeDate(record.date))
        .filter(Boolean);

    const latestStockDate =
        metadata.latest_stock_date || dates.sort().at(-1);

    const companyTickers = new Set(
        stockData.map((record) => record.ticker)
    );

    const signalDates = signalData
        .map((record) => normalizeDate(record.date))
        .filter(Boolean);

    const latestSignalDate =
        metadata.latest_signal_date || signalDates.sort().at(-1);

    const latestSignals = signalData.filter(
        (record) => normalizeDate(record.date) === latestSignalDate
    );

    const buySignals = latestSignals.filter(
        (record) => numberValue(record.signal_score) === 1
    );

    elements.latestDate.textContent = latestStockDate || "Unavailable";
    elements.companyCount.textContent =
        companyTickers.size.toLocaleString("en-NG");
    elements.recordCount.textContent =
        stockData.length.toLocaleString("en-NG");
    elements.buySignalCount.textContent =
        buySignals.length.toLocaleString("en-NG");

    if (metadata.generated_at) {
        const generatedDate = new Date(metadata.generated_at);

        elements.lastUpdated.textContent =
            `Data generated ${generatedDate.toLocaleString()}`;
    } else {
        elements.lastUpdated.textContent =
            `Latest market date: ${latestStockDate}`;
    }
}

function renderChart() {
    const selectedTicker = elements.companySelect.value;
    const selectedChartType = elements.chartType.value;
    const isMobile = mobileViewport.matches;

    const history = stockData
        .filter((record) => record.ticker === selectedTicker)
        .sort(
            (a, b) =>
                new Date(normalizeDate(a.date)) -
                new Date(normalizeDate(b.date))
        );

    if (!history.length) {
        return;
    }

    const companyName =
        history[0].company_name || selectedTicker;

    elements.chartTitle.textContent =
        `${companyName} (${selectedTicker}) Price History`;

    let traces;

    if (selectedChartType === "candlestick") {
        traces = [
            {
                type: "candlestick",
                x: history.map((record) => normalizeDate(record.date)),
                open: history.map((record) => numberValue(record.open)),
                high: history.map((record) => numberValue(record.high)),
                low: history.map((record) => numberValue(record.low)),
                close: history.map((record) => numberValue(record.close)),
                increasing: { line: { color: "#08783e" } },
                decreasing: { line: { color: "#c93636" } }
            }
        ];
    } else {
        traces = [
            {
                type: "scatter",
                mode: isMobile ? "lines" : "lines+markers",
                x: history.map((record) => normalizeDate(record.date)),
                y: history.map((record) => numberValue(record.close)),
                name: "Closing price",
                line: {
                    color: "#08783e",
                    width: 3
                },
                marker: {
                    size: 6
                }
            }
        ];
    }

    const layout = {
        autosize: true,
        height: isMobile ? 330 : 460,
        margin: isMobile
            ? { top: 10, right: 8, bottom: 42, left: 48 }
            : { top: 20, right: 25, bottom: 55, left: 65 },
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        xaxis: {
            title: isMobile ? "" : "Trading date",
            gridcolor: "#e7eeea",
            automargin: true,
            nticks: isMobile ? 5 : undefined,
            tickfont: { size: isMobile ? 10 : 12 },
            rangeslider: {
                visible: selectedChartType === "candlestick" && !isMobile
            }
        },
        yaxis: {
            title: isMobile ? "" : "Price (NGN)",
            gridcolor: "#e7eeea",
            automargin: true,
            tickfont: { size: isMobile ? 10 : 12 }
        },
        showlegend: selectedChartType === "line" && !isMobile
    };

    Plotly.newPlot(
        "priceChart",
        traces,
        layout,
        {
            responsive: true,
            displaylogo: false,
            displayModeBar: !isMobile,
            scrollZoom: false
        }
    );
}

function calculateLatestPrices() {
    const period = Number(elements.changePeriod.value);

    const grouped = new Map();

    stockData.forEach((record) => {
        if (!grouped.has(record.ticker)) {
            grouped.set(record.ticker, []);
        }

        grouped.get(record.ticker).push(record);
    });

    latestPrices = [];

    grouped.forEach((records, ticker) => {
        records.sort(
            (a, b) =>
                new Date(normalizeDate(a.date)) -
                new Date(normalizeDate(b.date))
        );

        const latest = records.at(-1);
        const latestDate = new Date(normalizeDate(latest.date));
        const targetDate = new Date(latestDate);

        targetDate.setDate(targetDate.getDate() - period);

        const previous =
            [...records]
                .reverse()
                .find(
                    (record) =>
                        new Date(normalizeDate(record.date)) <= targetDate
                ) || records[0];

        const latestClose = numberValue(latest.close);
        const previousClose = numberValue(previous.close);

        const percentageChange =
            previousClose !== 0
                ? ((latestClose - previousClose) / previousClose) * 100
                : 0;

        latestPrices.push({
            ...latest,
            ticker,
            percentageChange
        });
    });

    latestPrices.sort((a, b) =>
        String(a.company_name || a.ticker).localeCompare(
            String(b.company_name || b.ticker)
        )
    );
}

function renderStockTable() {
    calculateLatestPrices();

    const searchTerm =
        elements.stockSearch.value.trim().toLowerCase();

    const filtered = latestPrices.filter((record) => {
        const company = String(record.company_name || "").toLowerCase();
        const ticker = String(record.ticker || "").toLowerCase();

        return (
            company.includes(searchTerm) ||
            ticker.includes(searchTerm)
        );
    });

    elements.changeHeader.textContent =
        `${elements.changePeriod.value}-Day Change`;

    if (!filtered.length) {
        elements.stockTableBody.innerHTML =
            `<tr><td colspan="8">No matching companies found.</td></tr>`;
        return;
    }

    elements.stockTableBody.innerHTML = filtered
        .map((record) => {
            const changeClass =
                record.percentageChange >= 0 ? "positive" : "negative";

            const changePrefix =
                record.percentageChange > 0 ? "+" : "";

            const changeLabel =
                `${elements.changePeriod.value}-Day Change`;

            return `
                <tr>
                    <td data-label="Company">${escapeHtml(record.company_name || record.ticker)}</td>
                    <td data-label="Ticker">${escapeHtml(record.ticker)}</td>
                    <td data-label="Open">₦${formatPrice(record.open)}</td>
                    <td data-label="High">₦${formatPrice(record.high)}</td>
                    <td data-label="Low">₦${formatPrice(record.low)}</td>
                    <td data-label="Close">₦${formatPrice(record.close)}</td>
                    <td data-label="Volume">${formatVolume(record.volume)}</td>
                    <td data-label="${changeLabel}" class="${changeClass}">
                        ${changePrefix}${record.percentageChange.toFixed(2)}%
                    </td>
                </tr>
            `;
        })
        .join("");
}

function getLatestSignals() {
    if (!signalData.length) return [];

    const latestDate = signalData
        .map((record) => normalizeDate(record.date))
        .filter(Boolean)
        .sort()
        .at(-1);

    return signalData
        .filter((record) => normalizeDate(record.date) === latestDate)
        .sort(
            (a, b) =>
                numberValue(b.signal_score) -
                numberValue(a.signal_score)
        );
}

function renderSignalTable() {
    const latestSignals = getLatestSignals();

    if (!latestSignals.length) {
        elements.signalTableBody.innerHTML =
            `<tr><td colspan="7">No weekly signals are available.</td></tr>`;
        return;
    }

    elements.signalTableBody.innerHTML = latestSignals
        .map((record) => {
            const isBuy = numberValue(record.signal_score) === 1;

            return `
                <tr>
                    <td data-label="Company">${escapeHtml(record.company_name || record.ticker)}</td>
                    <td data-label="Ticker">${escapeHtml(record.ticker)}</td>
                    <td data-label="Date">${escapeHtml(normalizeDate(record.date))}</td>
                    <td data-label="RSI">${formatIndicator(record.rsi)}</td>
                    <td data-label="MACD">${formatIndicator(record.macd)}</td>
                    <td data-label="5-Day Return" class="${
                        numberValue(record.five_day_return) >= 0
                            ? "positive"
                            : "negative"
                    }">
                        ${formatIndicator(record.five_day_return)}%
                    </td>
                    <td data-label="Signal">
                        <span class="${isBuy ? "signal-buy" : "signal-hold"}">
                            ${isBuy ? "BUY" : "HOLD"}
                        </span>
                    </td>
                </tr>
            `;
        })
        .join("");
}

function downloadLatestSignals() {
    const latestSignals = getLatestSignals();

    if (!latestSignals.length) {
        alert("No signal data is currently available.");
        return;
    }

    const headers = [
        "company_name",
        "ticker",
        "date",
        "rsi",
        "macd",
        "five_day_return",
        "signal_score"
    ];

    const csvRows = [
        headers.join(","),
        ...latestSignals.map((record) =>
            headers
                .map((header) => {
                    const value =
                        header === "date"
                            ? normalizeDate(record[header])
                            : record[header];

                    return `"${String(value ?? "").replaceAll('"', '""')}"`;
                })
                .join(",")
        )
    ];

    const blob = new Blob(
        [csvRows.join("\n")],
        { type: "text/csv;charset=utf-8" }
    );

    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = "naijastock-weekly-signals.csv";
    link.click();

    URL.revokeObjectURL(downloadUrl);
}

function attachEventListeners() {
    elements.companySelect.addEventListener("change", renderChart);
    elements.chartType.addEventListener("change", renderChart);
    elements.changePeriod.addEventListener("change", renderStockTable);
    elements.stockSearch.addEventListener("input", renderStockTable);
    elements.downloadSignals.addEventListener(
        "click",
        downloadLatestSignals
    );

    let resizeTimer;

    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);

        resizeTimer = setTimeout(() => {
            const isMobile = mobileViewport.matches;

            if (isMobile !== previousMobileLayout) {
                previousMobileLayout = isMobile;
                renderChart();
            } else if (window.Plotly) {
                Plotly.Plots.resize("priceChart");
            }
        }, 150);
    });
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorPanel.classList.remove("hidden");
    elements.lastUpdated.textContent = "Data unavailable";
}

loadDashboard();
