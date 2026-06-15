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
  document.querySelector("#runtime-mode").value = settings.runtime_mode || "local";
  document.querySelector("#public-api-base-url").value =
    settings.public_api_base_url || "";
  document.querySelector("#daily-session-url").value =
    settings.daily_session_url || "";
  document.querySelector("#eigi-agent-id").value = settings.agent_id || "";
  document.querySelector("#dynamic-variables").value = JSON.stringify(
    settings.dynamic_variables || {},
    null,
    2,
  );
  document.querySelector("#conversation-config-type").value =
    settings.conversation_config_type || "VOICE";
  document.querySelector("#is-test-call").checked = Boolean(
    settings.is_test_call,
  );
  document.querySelector("#native-bin").value = settings.native_bin || "";
  document.querySelector("#native-config-file").value =
    settings.native_config_file || "";
  document.querySelector("#api-key-preview").textContent =
    settings.api_key_configured
      ? `API key loaded from .env: ${settings.api_key_preview}`
      : "API key is not configured. Set EIGI_API_KEY in .env.";
}

async function loadApiKeyStatus() {
  const status = await request("/api/remote-voice/api-keys");
  const list = document.querySelector("#api-key-status");
  list.innerHTML = "";
  Object.entries(status).forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <strong>${key}</strong>
      <span class="badge ${value.configured ? "" : "off"}">${value.configured ? value.preview : "missing"}</span>
    `;
    list.appendChild(row);
  });
}

async function loadAgents() {
  setMessage("Loading Eigi agents...");
  const payload = await request("/api/remote-voice/agents?page_size=100");
  const agents = payload.agents || [];
  const select = document.querySelector("#agent-select");
  const currentAgentId = document.querySelector("#eigi-agent-id").value;
  select.innerHTML = '<option value="">Select an agent</option>';
  agents.forEach((agent) => {
    const option = document.createElement("option");
    option.value = agent.id;
    option.textContent = agent.agent_name
      ? `${agent.agent_name} (${agent.id})`
      : agent.id;
    option.dataset.dynamicVariables = JSON.stringify(
      agent.dynamic_variables || [],
    );
    select.appendChild(option);
  });
  if (currentAgentId) {
    select.value = currentAgentId;
  }
  setMessage(`Loaded ${agents.length} agents.`);
}

async function loadDynamicVariables(agentId) {
  const list = document.querySelector("#dynamic-variable-list");
  list.innerHTML = "";
  if (!agentId) {
    return;
  }
  const payload = await request(
    `/api/remote-voice/agents/${encodeURIComponent(agentId)}/dynamic-variables`,
  );
  const variables = payload.dynamic_variables || [];
  if (!variables.length) {
    const row = document.createElement("div");
    row.className = "row";
    row.textContent = "No dynamic variables configured for this agent.";
    list.appendChild(row);
    return;
  }
  variables.forEach((variable) => {
    const name = variable.name || variable.key || variable.variable || "";
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${name}</strong>
        <span class="muted">${variable.description || variable.type || ""}</span>
      </div>
    `;
    list.appendChild(row);
  });
}

function parseJsonObject(selector, label) {
  const raw = document.querySelector(selector).value.trim();
  if (!raw) {
    return {};
  }
  const parsed = JSON.parse(raw);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed;
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
        loadApiKeyStatus(),
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
document.querySelector("#load-agents").addEventListener("click", loadAgents);

document.querySelector("#agent-select").addEventListener("change", async () => {
  const agentId = document.querySelector("#agent-select").value;
  document.querySelector("#eigi-agent-id").value = agentId;
  await loadDynamicVariables(agentId);
});

document.querySelector("#public-api-base-url").addEventListener("change", () => {
  const baseUrl = document.querySelector("#public-api-base-url").value.trim();
  if (baseUrl) {
    document.querySelector("#daily-session-url").value =
      `${baseUrl.replace(/\/$/, "")}/daily`;
  }
});

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
    let dynamicVariables;
    try {
      dynamicVariables = parseJsonObject(
        "#dynamic-variables",
        "Dynamic variables",
      );
    } catch (error) {
      setMessage(error.message);
      return;
    }
    const agentId = document.querySelector("#eigi-agent-id").value.trim();
    const payload = {
      runtime_mode: document.querySelector("#runtime-mode").value,
      public_api_base_url: document.querySelector("#public-api-base-url").value,
      daily_session_url: document.querySelector("#daily-session-url").value,
      agent_id: agentId,
      conversation_metadata: {
        agent_id: agentId,
        dynamic_variables: dynamicVariables,
      },
      dynamic_variables: dynamicVariables,
      conversation_visibility: false,
      conversation_config_type: document.querySelector(
        "#conversation-config-type",
      ).value,
      is_test_call: document.querySelector("#is-test-call").checked,
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

document
  .querySelector("#api-key-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = {
      EIGI_API_KEY: document.querySelector("#eigi-api-key").value,
      OPENAI_API_KEY: document.querySelector("#openai-api-key").value,
      DEEPGRAM_API_KEY: document.querySelector("#deepgram-api-key").value,
      CARTESIA_API_KEY: document.querySelector("#cartesia-api-key").value,
    };
    const payload = {};
    Object.entries(values).forEach(([key, value]) => {
      if (value.trim()) {
        payload[key] = value.trim();
      }
    });
    await request("/api/remote-voice/api-keys", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    document.querySelector("#api-key-form").reset();
    await Promise.all([loadApiKeyStatus(), loadRemoteVoiceSettings()]);
    setMessage("API keys saved.");
  });
