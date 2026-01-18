let map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

let marker = null;
let polyline = L.polyline([], {color: 'red'}).addTo(map);
let firstFix = false;
let polylineEnabled = true;

async function fetchLocation() {
    try {
        let response = await fetch('/latest');
        if (response.ok) {
            let data = await response.json();
            if (data.lat && data.lon) {
                // update map
                if (!firstFix) {
                    map.setView([data.lat, data.lon], 15);
                    marker = L.marker([data.lat, data.lon]).addTo(map)
                        .bindPopup(`📍 ${data.address}<br>🕒 ${data.timestamp}`).openPopup();
                    document.getElementById("status").className = "alert alert-success text-center m-2 py-1";
                    document.getElementById("status").textContent = `✅ Device Connected (${data.device_name})`;
                    firstFix = true;
                } else {
                    marker.setLatLng([data.lat, data.lon]);
                    marker.getPopup().setContent(`📍 ${data.address}<br>🕒 ${data.timestamp}`);
                    map.panTo([data.lat, data.lon]);
                }

                // ✅ update satellites info
                const satDiv = document.getElementById("satellite-info");
                const satCount = document.getElementById("satellite-count");
                satCount.textContent = data.satellites || 0;
                satDiv.style.display = "block";
            }
        } else {
            // ถ้าไม่มีข้อมูล
            document.getElementById("status").className = "alert alert-secondary text-center m-2 py-1";
            document.getElementById("status").textContent = "⏳ Waiting for Device Connected";
            document.getElementById("satellite-info").style.display = "none";
        }
    } catch (err) {
        console.error(err);
        document.getElementById("status").className = "alert alert-danger text-center m-2 py-1";
        document.getElementById("status").textContent = "⚠️ Device Offline";
        document.getElementById("satellite-info").style.display = "none";
    }
}


async function fetchHistory() {
    try {
        let response = await fetch('/history');
        if (response.ok) {
            let data = await response.json();
            let latlngs = data.map(d => [d.lat, d.lon]);
            if (polylineEnabled) polyline.setLatLngs(latlngs);
            else polyline.setLatLngs([]);

            let logs = document.getElementById("logs");
            logs.innerHTML = "";
            data.slice(-10).reverse().forEach(d => {
                let item = document.createElement("div");
                item.className = "log-item list-group-item list-group-item-light";
                item.innerHTML = `<b>📍 ${d.address}</b><br><small>${d.timestamp}</small>`;
                logs.appendChild(item);
            });
        }
    } catch(err) { console.error(err); }
}

async function checkStatus() {
    try {
        let response = await fetch('/status');
        if (response.ok) {
            let data = await response.json();
            let statusDiv = document.getElementById("status");
            if (data.connected) {
                statusDiv.className = "alert alert-success text-center m-2 py-1";
                statusDiv.textContent = `✅ Device Connected: ${data.device.name}`;
            } else {
                statusDiv.className = "alert alert-danger text-center m-2 py-1";
                statusDiv.textContent = "❌ Device Offline";
            }
        }
    } catch(err) { console.error(err); }
}

async function clearLogs() {
    if (!confirm("คุณต้องการลบประวัติทั้งหมดใช่หรือไม่?")) return;
    try {
        let response = await fetch('/clear_logs', { method: 'POST' });
        if (response.ok) {
            let data = await response.json();
            if (data.status === "success") {
                alert("🧹 ลบประวัติเรียบร้อยแล้ว!");
                document.getElementById("logs").innerHTML = "";
                polyline.setLatLngs([]);
                if (marker) {
                    marker.remove();
                    marker = null;
                    firstFix = false;
                }
            } else {
                alert("❌ ลบไม่สำเร็จ: " + data.msg);
            }
        }
    } catch (err) {
        console.error(err);
        alert("เกิดข้อผิดพลาดในการลบข้อมูล");
    }
}

// ✅ Event Listener
document.getElementById("clearLogBtn").addEventListener("click", clearLogs);


document.getElementById("togglePolyline").addEventListener("change", function(e){
    polylineEnabled = e.target.checked;
    if(!polylineEnabled) polyline.setLatLngs([]);
});

setInterval(()=>{
    checkStatus();
    fetchLocation();
    fetchHistory();
}, 5000);
