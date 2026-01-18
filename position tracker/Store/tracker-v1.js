let map = L.map('map').setView([13.736717, 100.523186], 12);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let marker = null;
let polyline = null;
let polylinePoints = [];

const statusEl = document.getElementById("status");
const toggleGeocode = document.getElementById("toggleGeocode");
const togglePolyline = document.getElementById("togglePolyline");
const geocodeStatusEl = document.getElementById("geocodeStatus");
const logsEl = document.getElementById("logs");

function addLog(msg) {
    const el = document.createElement("div");
    el.className = "list-group-item small";
    el.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logsEl.prepend(el);
    while (logsEl.children.length > 20) {
        logsEl.removeChild(logsEl.lastChild);
    }
}

async function checkStatus() {
    try {
        let res = await fetch('/status');
        let data = await res.json();
        let statusEl = document.getElementById('status');
        let geoEl = document.getElementById('geocodeStatus');

        if (data.status === 'online') {
            statusEl.className = "alert alert-success text-center m-2 py-1";
            statusEl.textContent = "✅ Device Online";

            if (data.device) {
                if (data.device.address && data.device.address !== "Unknown") {
                    geoEl.className = "alert alert-success text-center m-2 py-1";
                    geoEl.textContent = "📍 " + data.device.address;
                } else {
                    geoEl.className = "alert alert-warning text-center m-2 py-1";
                    geoEl.textContent = "📍 Address not available";
                }
            }
        } else {
            statusEl.className = "alert alert-secondary text-center m-2 py-1";
            statusEl.textContent = "⏳ Waiting for Device Connected";

            geoEl.className = "alert alert-secondary text-center m-2 py-1";
            geoEl.textContent = "⏳ Checking geocoding service...";
        }
    } catch (e) {
        console.error("Status check error:", e);
    }
}

setInterval(checkStatus, 3000);

async function checkGeocode() {
    try {
        const res = await fetch("/check_geocoding");
        const data = await res.json();
        if (data.status === "ok") {
            geocodeStatusEl.className = "alert alert-success text-center m-2 py-1";
            geocodeStatusEl.textContent = "✅ Geocoding service available";
        } else {
            throw new Error("down");
        }
    } catch {
        geocodeStatusEl.className = "alert alert-danger text-center m-2 py-1";
        geocodeStatusEl.textContent = "❌ Geocoding service unavailable";
    }
}

async function loadHistory() {
    const res = await fetch("/history");
    const data = await res.json();
    if (Array.isArray(data)) {
        polylinePoints = data.reverse().map(d => [d.latitude, d.longitude]);
        if (togglePolyline.checked && polylinePoints.length > 1) {
            if (polyline) map.removeLayer(polyline);
            polyline = L.polyline(polylinePoints, { color: "blue" }).addTo(map);
            map.fitBounds(polyline.getBounds());
        }
    }
}

async function pollStatus() {
    try {
        const res = await fetch("/status");
        const data = await res.json();

        if (data.connected && data.device) {
            const dev = data.device;
            const latlng = [dev.latitude, dev.longitude];

            statusEl.className = "alert alert-success text-center m-2 py-1";
            statusEl.textContent = `✅ ${dev.name} Online`;

            if (marker) {
                marker.setLatLng(latlng);
            } else {
                marker = L.marker(latlng).addTo(map);
            }

            let popupContent = `<b>${dev.name}</b><br>Lat: ${dev.latitude}, Lon: ${dev.longitude}`;
            if (toggleGeocode.checked && dev.address) {
                popupContent += `<br>${dev.address}`;
            }
            marker.bindPopup(popupContent).openPopup();

            polylinePoints.push(latlng);
            if (togglePolyline.checked && polylinePoints.length > 1) {
                if (polyline) map.removeLayer(polyline);
                polyline = L.polyline(polylinePoints, { color: "blue" }).addTo(map);
            }

            addLog(`${dev.name}: ${dev.latitude}, ${dev.longitude} - ${dev.address || ""}`);
        } else {
            statusEl.className = "alert alert-secondary text-center m-2 py-1";
            statusEl.textContent = "⏳ Waiting for Device Connected";
        }
    } catch (err) {
        console.error("Status poll failed", err);
    }
}

checkGeocode();
loadHistory();
setInterval(pollStatus, 5000);
