// tracker.js (updated for Flask + history + online check)
document.addEventListener("DOMContentLoaded", function () {
  console.log("Tracker JS Loaded ✅");

  const map = L.map("map").setView([13.736717, 100.523186], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const markers = {};
  const polylines = {};
  const logsDiv = document.getElementById("logs");
  const statusDiv = document.getElementById("status");

  let polylineEnabled = true;
  let geocodeEnabled = true;
  const LAST_SEEN_THRESHOLD = 30; // วินาที

  document.getElementById("togglePolyline")?.addEventListener("change", e => {
    polylineEnabled = e.target.checked;
    if (!polylineEnabled) {
      Object.values(polylines).forEach(p => p.setLatLngs([]));
    }
  });

  document.getElementById("toggleGeocode")?.addEventListener("change", e => {
    geocodeEnabled = e.target.checked;
  });

  // -----------------------------
  // Helper fetch JSON
  // -----------------------------
  async function fetchJSON(url, options = {}) {
    const resp = await fetch(url, options);
    return await resp.json();
  }

  // -----------------------------
  // Update status / map / log
  // -----------------------------
  async function fetchStatus() {
    try {
      const latestResp = await fetchJSON("/latest");

      if (!latestResp.device) {
        statusDiv.textContent = "⏳ Waiting for Device Connected";
        return;
      }

      const device = latestResp.device;
      const lastTs = new Date(device.timestamp);
      const now = new Date();
      const diffSec = (now - lastTs) / 1000;

      if (diffSec > LAST_SEEN_THRESHOLD) {
        statusDiv.textContent = "⏳ Waiting for Device Connected";
      } else {
        statusDiv.textContent = `✅ Device Connected: ${device.name}`;
      }

      // update map marker
      if (!markers[device.name]) {
        markers[device.name] = L.marker([device.latitude, device.longitude])
          .addTo(map)
          .bindPopup(getPopupContent(device));
      } else {
        markers[device.name].setLatLng([device.latitude, device.longitude]);
        markers[device.name].getPopup().setContent(getPopupContent(device));
      }

      // fetch history for polyline
      const historyResp = await fetchJSON("/history");
      if (historyResp.length) {
        const latlngs = historyResp.map(d => [d.latitude, d.longitude]);
        if (!polylines[device.name]) {
          polylines[device.name] = L.polyline(latlngs, { color: "red" }).addTo(map);
        } else if (polylineEnabled) {
          polylines[device.name].setLatLngs(latlngs);
        }
      }

      // add log
      addLog(`${device.name} @ ${device.latitude},${device.longitude} - ${device.address || "Unknown"}`);
    } catch (err) {
      console.error("Error fetching status:", err);
      statusDiv.textContent = "⚠️ Error fetching device status";
    }
  }

  function getPopupContent(device) {
    if (geocodeEnabled && device.address) {
      return `📍 ${device.name}<br>${device.address}<br>Lat: ${device.latitude}, Lon: ${device.longitude}`;
    } else {
      return `📍 ${device.name}<br>Lat: ${device.latitude}, Lon: ${device.longitude}`;
    }
  }

  function addLog(text) {
    const item = document.createElement("div");
    item.className = "list-group-item py-1";
    item.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    logsDiv.prepend(item);
    if (logsDiv.children.length > 50) logsDiv.removeChild(logsDiv.lastChild);
  }

  // -----------------------------
  // Auto-refresh
  // -----------------------------
  fetchStatus();
  setInterval(fetchStatus, 5000);
});
