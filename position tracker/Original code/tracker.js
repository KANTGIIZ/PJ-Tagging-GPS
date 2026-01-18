let map = L.map('map').setView([13.7563, 100.5018], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

let marker = null;
let polyline = L.polyline([], {color: 'blue'}).addTo(map);

async function fetchLatest() {
    let res = await fetch('/latest');
    let data = await res.json();
    if (data.latitude && data.longitude) {
        let latlng = [data.latitude, data.longitude];
        if (!marker) {
            marker = L.marker(latlng).addTo(map);
        } else {
            marker.setLatLng(latlng);
        }
        map.setView(latlng, 13);
        polyline.addLatLng(latlng);
        addLog(data);
    }
}

async function fetchStatus() {
    let res = await fetch('/status');
    let data = await res.json();
    document.getElementById('status').innerText = data.status.toUpperCase();
    document.getElementById('status').style.color = (data.status === "online") ? "green" : "red";
}

function addLog(data) {
    let logs = document.getElementById("logs");
    let li = document.createElement("li");
    let ts = new Date(data.timestamp * 1000).toLocaleString();
    li.textContent = `${ts} - ${data.latitude}, ${data.longitude} - ${data.address}`;
    logs.prepend(li);
    if (logs.childNodes.length > 10) {
        logs.removeChild(logs.lastChild);
    }
}

setInterval(fetchLatest, 5000);
setInterval(fetchStatus, 5000);

fetchLatest();
fetchStatus();
