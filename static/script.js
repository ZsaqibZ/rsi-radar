// On Load
document.addEventListener('DOMContentLoaded', () => {
    fetchScan();
    // Auto refresh every 3 minutes
    setInterval(fetchScan, 180000); 
});

async function fetchScan() {
    const btn = document.getElementById('refresh-btn');
    const status = document.getElementById('status-bar');
    const minMcap = document.getElementById('min-mcap').value;

    // UI Loading State
    btn.disabled = true;
    btn.innerText = "Scanning...";
    status.innerText = "Fetching market data (this may take ~20s)...";

    try {
        // Call Python Backend
        const response = await fetch(`/api/scan?min_mcap=${minMcap}`);
        const data = await response.json();
        
        renderTable(data);
        
        const now = new Date().toLocaleTimeString();
        status.innerText = `Last updated: ${now} | Found ${data.length} coins`;

    } catch (error) {
        console.error('Error:', error);
        status.innerText = "Error fetching data.";
    } finally {
        btn.disabled = false;
        btn.innerText = "SCAN MARKET";
    }
}

function renderTable(data) {
    const tbody = document.getElementById('scan-results');
    const oversoldLimit = parseInt(document.getElementById('oversold-limit').value);
    const overboughtLimit = parseInt(document.getElementById('overbought-limit').value);

    tbody.innerHTML = ''; // Clear old data

    data.forEach(coin => {
        const tr = document.createElement('tr');

        // Helper to format market cap
        let mcapDisplay = "N/A";
        if (coin.mcap > 0) {
            mcapDisplay = "$" + (coin.mcap / 1_000_000_000).toFixed(2) + "B";
        }

        // Helper to determine color class
        const getColorClass = (rsi) => {
            if (rsi <= 0) return 'rsi-neutral';
            if (rsi <= oversoldLimit) return 'rsi-oversold';
            if (rsi >= overboughtLimit) return 'rsi-overbought';
            return 'rsi-neutral';
        };

        tr.innerHTML = `
            <td style="font-weight:bold;">
                <a href="https://www.tradingview.com/chart/?symbol=${coin.symbol}USD" target="_blank" style="text-decoration:none; color:inherit;">
                    ${coin.symbol}
                </a>
            </td>
            <td>$${coin.price}</td>
            <td>${mcapDisplay}</td>
            <td><span class="rsi-box ${getColorClass(coin.rsi_15m)}">${coin.rsi_15m}</span></td>
            <td><span class="rsi-box ${getColorClass(coin.rsi_1h)}">${coin.rsi_1h}</span></td>
            <td><span class="rsi-box ${getColorClass(coin.rsi_4h)}">${coin.rsi_4h}</span></td>
            <td><span class="rsi-box ${getColorClass(coin.rsi_1d)}">${coin.rsi_1d}</span></td>
            <td>
                <button class="btn-del" onclick="removeCoin('${coin.ticker}')">X</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function addCoin() {
    const input = document.getElementById('new-ticker');
    const ticker = input.value;
    if(!ticker) return;

    await fetch('/api/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ticker: ticker})
    });

    input.value = ''; // Clear input
    fetchScan(); // Refresh data
}

async function removeCoin(ticker) {
    if(!confirm(`Remove ${ticker}?`)) return;

    await fetch('/api/remove', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ticker: ticker})
    });

    fetchScan(); // Refresh data
}