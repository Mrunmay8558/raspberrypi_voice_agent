const loginPanel = document.querySelector("#login-panel");
const dashboardPanel = document.querySelector("#dashboard-panel");
const loginMessage = document.querySelector("#login-message");
const appMessage = document.querySelector("#app-message");

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the generic error.
    }
    throw new Error(detail);
  }
  return response.json();
}

function showDashboard() {
  loginPanel.classList.add("hidden");
  dashboardPanel.classList.remove("hidden");
}

function setMessage(text) {
  appMessage.textContent = text;
}

async function loadStatus() {
  const status = await request("/api/system/status");
  document.querySelector("#local-url").textContent = status.local_url;
  const services = document.querySelector("#services");
  services.innerHTML = "";
  status.services.forEach((service) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${service.name}</strong>
        <span class="muted">${service.sub_state}</span>
      </div>
      <span class="badge ${service.active ? "" : "off"}">${service.active ? "active" : "check"}</span>
    `;
    services.appendChild(row);
  });
}

async function loadWifi() {
  setMessage("Scanning WiFi networks...");
  const networks = await request("/api/wifi/networks");
  const list = document.querySelector("#wifi-list");
  list.innerHTML = "";
  networks.forEach((network) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "row secondary";
    row.innerHTML = `<span>${network.ssid}</span><span>${network.signal ?? "-"}%</span>`;
    row.addEventListener("click", () => {
      document.querySelector("#wifi-ssid").value = network.ssid;
    });
    list.appendChild(row);
  });
  setMessage("");
}

async function loadBluetooth(scan = false) {
  setMessage(
    scan ? "Scanning Bluetooth devices..." : "Loading Bluetooth devices...",
  );
  const devices = await request(
    scan ? "/api/bluetooth/scan" : "/api/bluetooth/devices",
    {
      method: scan ? "POST" : "GET",
    },
  );
  const list = document.querySelector("#bluetooth-list");
  list.innerHTML = "";
  devices.forEach((device) => {
    const row = document.createElement("div");
    row.className = "row";
    const action = device.connected ? "Disconnect" : "Connect";
    row.innerHTML = `
      <div>
        <strong>${device.name}</strong>
        <span class="muted">${device.mac}</span>
      </div>
      <button type="button">${action}</button>
    `;
    row.querySelector("button").addEventListener("click", async () => {
      const path = device.connected
        ? `/api/bluetooth/disconnect/${encodeURIComponent(device.mac)}`
        : "/api/bluetooth/connect";
      const body = device.connected
        ? undefined
        : JSON.stringify({ mac: device.mac, pair: true, trust: true });
      await request(path, { method: "POST", body });
      await loadBluetooth(false);
    });
    list.appendChild(row);
  });
  setMessage("");
}

async function loadRemoteVoiceSettings() {
  const settings = await request("/api/remote-voice/settings");
  document.querySelector("#daily-session-url").value =
    settings.daily_session_url || "";
  document.querySelector("#eigi-agent-id").value = settings.agent_id || "";
  document.querySelector("#conversation-config-type").value =
    settings.conversation_config_type || "VOICE";
  document.querySelector("#voice-client-type").value =
    settings.client_type || "native";
  document.querySelector("#native-bin").value = settings.native_bin || "";
  document.querySelector("#native-config-file").value =
    settings.native_config_file || "";
  document.querySelector("#api-key-preview").textContent =
    settings.api_key_configured
      ? `API key loaded from .env: ${settings.api_key_preview}`
      : "API key is not configured. Set EIGI_API_KEY in .env.";
}

document
  .querySelector("#login-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    loginMessage.textContent = "";
    try {
      await request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: document.querySelector("#username").value,
          password: document.querySelector("#password").value,
        }),
      });
      showDashboard();
      await Promise.all([
        loadStatus(),
        loadWifi(),
        loadBluetooth(false),
        loadRemoteVoiceSettings(),
      ]);
    } catch (error) {
      loginMessage.textContent = error.message;
    }
  });

document.querySelector("#logout-button").addEventListener("click", async () => {
  await request("/api/auth/logout", { method: "POST", body: "{}" });
  window.location.reload();
});

document.querySelector("#refresh-status").addEventListener("click", loadStatus);
document.querySelector("#scan-wifi").addEventListener("click", loadWifi);
document
  .querySelector("#scan-bluetooth")
  .addEventListener("click", () => loadBluetooth(true));

document
  .querySelector("#wifi-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Connecting WiFi...");
    await request("/api/wifi/connect", {
      method: "POST",
      body: JSON.stringify({
        ssid: document.querySelector("#wifi-ssid").value,
        password: document.querySelector("#wifi-password").value,
      }),
    });
    setMessage("WiFi connection command completed.");
  });

document
  .querySelector("#password-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    await request("/api/auth/password", {
      method: "POST",
      body: JSON.stringify({
        username: document.querySelector("#password-username").value,
        current_password: document.querySelector("#current-password").value,
        new_password: document.querySelector("#new-password").value,
      }),
    });
    setMessage("Password changed. Log in again with the new password.");
  });

document
  .querySelector("#remote-voice-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      daily_session_url: document.querySelector("#daily-session-url").value,
      agent_id: document.querySelector("#eigi-agent-id").value,
      conversation_metadata: {
        agent_id: document.querySelector("#eigi-agent-id").value,
      },
      conversation_visibility: false,
      conversation_config_type: document.querySelector(
        "#conversation-config-type",
      ).value,
      client_type: document.querySelector("#voice-client-type").value,
      native_bin: document.querySelector("#native-bin").value,
      native_config_file: document.querySelector("#native-config-file").value,
    };
    await request("/api/remote-voice/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    await loadRemoteVoiceSettings();
    setMessage("Remote voice settings saved.");
  });
