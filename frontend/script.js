const API_BASE_URL = (window.MEDICTIME_CONFIG?.API_BASE_URL || "").replace(/\/$/, "");

const state = {
  mediaRecorder: null,
  recorderMode: null,
  recorderMimeType: "",
  voiceBlob: null,
  soapBlob: null,
  chunks: [],
  stream: null,
  voiceBusy: false,
  soapBusy: false,
};

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function appendChatMessage(role, text) {
  const log = document.getElementById("chat-log");
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

async function checkHealth() {
  const label = document.getElementById("api-status");
  document.getElementById("api-base-label").textContent = API_BASE_URL || "Using same-origin API";
  try {
    const response = await fetch(apiUrl("/health"));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    label.textContent = "API online";
  } catch (error) {
    label.textContent = "API unavailable";
  }
}

async function sendChat() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) {
    return;
  }

  appendChatMessage("user", message);
  input.value = "";

  const body = new FormData();
  body.append("message", message);

  try {
    const response = await fetch(apiUrl("/api/agent-chat"), { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }
    appendChatMessage("agent", data.response);
  } catch (error) {
    appendChatMessage("agent", `Request failed: ${error.message}`);
  }
}

async function startRecording(mode) {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    throw new Error("This browser does not support in-browser audio recording.");
  }
  state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  state.chunks = [];
  state.recorderMode = mode;
  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "";
  state.recorderMimeType = mimeType;
  state.mediaRecorder = mimeType
    ? new MediaRecorder(state.stream, { mimeType })
    : new MediaRecorder(state.stream);
  state.mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      state.chunks.push(event.data);
    }
  };
  state.mediaRecorder.onstop = () => {
    const blob = new Blob(state.chunks, { type: state.recorderMimeType || "audio/webm" });
    if (state.recorderMode === "voice") {
      state.voiceBlob = blob;
      document.getElementById("voice-send-btn").disabled = false;
      document.getElementById("voice-status").textContent = "Recording saved. Send it when ready.";
    } else if (state.recorderMode === "soap") {
      state.soapBlob = blob;
      document.getElementById("soap-use-recording-btn").disabled = false;
      document.getElementById("soap-status").textContent = "Consultation saved. Generate the SOAP note from the recording or choose a file instead.";
    }
    state.recorderMode = null;
    state.mediaRecorder = null;
    state.recorderMimeType = "";
    state.stream?.getTracks().forEach((track) => track.stop());
    state.stream = null;
  };
  state.mediaRecorder.start();
}

async function startVoiceRecording() {
  await startRecording("voice");
  document.getElementById("voice-status").textContent = "Recording...";
}

async function startSoapRecording() {
  await startRecording("soap");
  document.getElementById("soap-status").textContent = "Recording consultation...";
}

function stopVoiceRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
}

function speakText(text) {
  if (!("speechSynthesis" in window)) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

async function submitVoiceMessage() {
  if (!state.voiceBlob || state.voiceBusy) {
    return;
  }

  const body = new FormData();
  body.append("audio", state.voiceBlob, "voice.webm");
  state.voiceBusy = true;
  document.getElementById("voice-send-btn").disabled = true;
  document.getElementById("voice-status").textContent = "Uploading audio...";

  try {
    const response = await fetch(apiUrl("/api/voice-chat"), { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Voice request failed");
    }
    document.getElementById("voice-transcript").textContent = data.transcription;
    document.getElementById("voice-reply").textContent = data.response;
    document.getElementById("voice-status").textContent = "Reply ready. Spoken with browser TTS.";
    speakText(data.response);
  } catch (error) {
    document.getElementById("voice-status").textContent = error.message;
  } finally {
    state.voiceBusy = false;
    document.getElementById("voice-send-btn").disabled = false;
  }
}

async function generateSoap() {
  if (state.soapBusy) {
    return;
  }
  const fileInput = document.getElementById("soap-file");
  const file = fileInput.files?.[0];
  const audioSource = file || state.soapBlob;
  if (!audioSource) {
    document.getElementById("soap-status").textContent = "Choose an audio file or make a live recording first.";
    return;
  }

  const body = new FormData();
  body.append("audio", audioSource, file?.name || "consultation.webm");
  state.soapBusy = true;
  document.getElementById("soap-submit-btn").disabled = true;
  document.getElementById("soap-use-recording-btn").disabled = true;
  document.getElementById("soap-status").textContent = "Processing audio...";

  try {
    const response = await fetch(apiUrl("/api/soap-from-audio"), { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "SOAP generation failed");
    }
    document.getElementById("soap-transcript").textContent = data.transcription;
    document.getElementById("soap-note").textContent = data.soap;
    document.getElementById("soap-status").textContent = "SOAP note generated. Doctor and patient roles were inferred from the transcript.";
  } catch (error) {
    document.getElementById("soap-status").textContent = error.message;
  } finally {
    state.soapBusy = false;
    document.getElementById("soap-submit-btn").disabled = false;
    document.getElementById("soap-use-recording-btn").disabled = !state.soapBlob;
  }
}

document.getElementById("chat-send").addEventListener("click", sendChat);
document.getElementById("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendChat();
  }
});

document.getElementById("voice-record-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  if (!state.mediaRecorder || state.mediaRecorder.state === "inactive") {
    try {
      await startVoiceRecording();
      button.textContent = "Stop Recording";
    } catch (error) {
      document.getElementById("voice-status").textContent = error.message;
    }
  } else {
    stopVoiceRecording();
    button.textContent = "Start Recording";
  }
});

document.getElementById("soap-record-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  if (!state.mediaRecorder || state.mediaRecorder.state === "inactive") {
    try {
      await startSoapRecording();
      button.textContent = "Stop Live Recording";
    } catch (error) {
      document.getElementById("soap-status").textContent = error.message;
    }
  } else if (state.recorderMode === "soap") {
    stopVoiceRecording();
    button.textContent = "Start Live Recording";
  }
});

document.getElementById("soap-use-recording-btn").addEventListener("click", generateSoap);
document.getElementById("voice-send-btn").addEventListener("click", submitVoiceMessage);
document.getElementById("soap-submit-btn").addEventListener("click", generateSoap);
document.getElementById("soap-file").addEventListener("change", () => {
  state.soapBlob = null;
  document.getElementById("soap-use-recording-btn").disabled = true;
  document.getElementById("soap-status").textContent = "Audio file selected. Generate the SOAP note when ready.";
});

checkHealth();
