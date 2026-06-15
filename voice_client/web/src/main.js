import { PipecatClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import "./style.css";

const statusEl = document.querySelector("#status");
const transcriptEl = document.querySelector("#transcript");

function setStatus(value) {
  statusEl.textContent = value;
  postEvent("Status", { value });
}

async function postEvent(event, data = {}) {
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, data }),
    });
  } catch {
    // Event logging must not break the call.
  }
}

function safeData(data) {
  try {
    return JSON.parse(JSON.stringify(data));
  } catch {
    return String(data);
  }
}

const callbacks = {
  onConnected: () => {
    setStatus("Connected");
  },
  onDisconnected: () => {
    setStatus("Disconnected");
    window.close();
  },
  onTransportStateChanged: (state) => {
    postEvent("TransportStateChanged", safeData(state));
  },
  onBotConnected: () => {
    setStatus("Bot connected");
  },
  onBotReady: (data) => {
    setStatus("Bot ready");
    postEvent("BotReady", safeData(data));
  },
  onBotDisconnected: () => {
    setStatus("Bot disconnected");
    window.close();
  },
  onParticipantJoined: (participant) => {
    postEvent("ParticipantJoined", safeData(participant));
  },
  onParticipantLeft: (participant) => {
    postEvent("ParticipantLeft", safeData(participant));
  },
  onUserStartedSpeaking: () => {
    postEvent("UserStartedSpeaking");
  },
  onUserStoppedSpeaking: () => {
    postEvent("UserStoppedSpeaking");
  },
  onBotStartedSpeaking: () => {
    postEvent("BotStartedSpeaking");
  },
  onBotStoppedSpeaking: () => {
    postEvent("BotStoppedSpeaking");
  },
  onUserTranscript: (data) => {
    transcriptEl.textContent = data?.text ?? "";
    postEvent("UserTranscript", safeData(data));
  },
  onBotOutput: (data) => {
    postEvent("BotOutput", safeData(data));
  },
  onBotLlmText: (data) => {
    postEvent("BotLlmText", safeData(data));
  },
  onBotTtsText: (data) => {
    postEvent("BotTtsText", safeData(data));
  },
  onError: (data) => {
    setStatus("Error");
    postEvent("Error", safeData(data));
    if (data?.fatal) {
      window.close();
    }
  },
  onMessageError: (data) => {
    postEvent("MessageError", safeData(data));
  },
  onDeviceError: (data) => {
    setStatus("Device error");
    postEvent("DeviceError", safeData(data));
  },
  onMicUpdated: (data) => {
    postEvent("MicUpdated", safeData(data));
  },
  onSpeakerUpdated: (data) => {
    postEvent("SpeakerUpdated", safeData(data));
  },
  onTrackStarted: (data) => {
    postEvent("TrackStarted", safeData(data));
  },
  onTrackStopped: (data) => {
    postEvent("TrackStopped", safeData(data));
  },
  onServerMessage: (data) => {
    postEvent("ServerMessage", safeData(data));
  },
  onMetrics: (data) => {
    postEvent("Metrics", safeData(data));
  },
};

const client = new PipecatClient({
  transport: new DailyTransport(),
  enableMic: true,
  enableCam: false,
  callbacks,
});

async function start() {
  try {
    setStatus("Initializing devices");
    await client.initDevices();
    setStatus("Connecting to deployed bot");
    await client.startBotAndConnect({ endpoint: "/api/start" });
  } catch (error) {
    setStatus(`Failed: ${error.message}`);
    await postEvent("StartupError", { message: error.message, stack: error.stack });
  }
}

window.addEventListener("beforeunload", () => {
  try {
    client.disconnect();
  } catch {
    // Ignore shutdown race.
  }
});

start();
