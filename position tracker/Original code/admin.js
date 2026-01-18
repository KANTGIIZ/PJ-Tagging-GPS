document.addEventListener("DOMContentLoaded", function() {
    const adminModalEl = document.getElementById('adminLoginModal');
    const adminModal = new bootstrap.Modal(adminModalEl, { backdrop: 'static', keyboard: false });

    async function checkSession() {
        let resp = await fetch('/admin/check_session');
        let data = await resp.json();
        if (data.status === 'ok') {
            adminModal.hide();
            document.getElementById('adminContent').classList.remove('d-none');
            loadAdminData();
        } else {
            adminModal.show();
        }
    }

    checkSession();

    // Login form
    document.getElementById('adminLoginForm').addEventListener('submit', async function(e){
        e.preventDefault();
        const username = document.getElementById('adminUsername').value;
        const password = document.getElementById('adminPassword').value;
        const alertDiv = document.getElementById('loginAlert');
        alertDiv.classList.add('d-none');

        try {
            const response = await fetch('/admin/check_login', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({username, password})
            });
            const result = await response.json();
            if (result.status === 'ok') {
                adminModal.hide();
                document.getElementById('adminContent').classList.remove('d-none');
                loadAdminData();
            } else {
                alertDiv.textContent = result.msg;
                alertDiv.classList.remove('d-none');
            }
        } catch(err) {
            alertDiv.textContent = "Server error";
            alertDiv.classList.remove('d-none');
        }
    });

    // Logout
    document.getElementById('adminLogoutBtn').addEventListener('click', async () => {
        await fetch('/logout');
        location.reload();
    });

    // Load users/devices
    async function loadAdminData() {
        const resp = await fetch('/admin/data');
        const data = await resp.json();
        if (data.status === 'ok') {
            const usersBody = document.querySelector('#usersTable tbody');
            usersBody.innerHTML = '';
            data.users.forEach(u => {
                usersBody.innerHTML += `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.role}</td>
                    <td><button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">Delete</button></td>
                </tr>`;
            });

            const devicesBody = document.querySelector('#devicesTable tbody');
            devicesBody.innerHTML = '';
            data.devices.forEach(d => {
                devicesBody.innerHTML += `
                <tr>
                    <td>${d.id}</td>
                    <td>${d.device_name}</td>
                    <td>${d.user_id}</td>
                    <td>${d.owner}</td>
                    <td><button class="btn btn-danger btn-sm" onclick="deleteDevice(${d.id})">Delete</button></td>
                </tr>`;
            });
        }
    }

    // Add user/device
    document.getElementById('addUserForm').addEventListener('submit', async function(e){
        e.preventDefault();
        const formData = new FormData(this);
        await fetch('/admin/add_user', { method: 'POST', body: formData });
        loadAdminData();
        this.reset();
    });

    document.getElementById('addDeviceForm').addEventListener('submit', async function(e){
        e.preventDefault();
        const formData = new FormData(this);
        await fetch('/admin/add_device', { method: 'POST', body: formData });
        loadAdminData();
        this.reset();
    });

    // Delete functions
    window.deleteUser = async function(id) {
        await fetch(`/admin/delete_user/${id}`);
        loadAdminData();
    }
    window.deleteDevice = async function(id) {
        await fetch(`/admin/delete_device/${id}`);
        loadAdminData();
    }
});
