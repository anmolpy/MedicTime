const API = '';

function switchTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  document.getElementById('tab-'+name).classList.add('active');
}

let mediaRecorder = null;
let audioChunks = [];
let timerInterval = null;
let timerSeconds = 0;
let analyserNode = null;
let animFrameId = null;

const waveCanvas = document.getElementById('wave');
const waveCtx = waveCanvas.getContext('2d');
const wavePlaceholder = document.getElementById('wave-placeholder');

function drawWave(analyser) {
  const buf = new Uint8Array(analyser.frequencyBinCount);
  function frame() {
    animFrameId = requestAnimationFrame(frame);
    analyser.getByteTimeDomainData(buf);
    const W = waveCanvas.offsetWidth; const H = waveCanvas.offsetHeight;
    waveCanvas.width = W; waveCanvas.height = H;
    waveCtx.clearRect(0,0,W,H);
    waveCtx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--teal');
    waveCtx.lineWidth = 2;
    waveCtx.beginPath();
    const step = W / buf.length;
    buf.forEach((v, i) => {
      const y = (v / 128.0) * H / 2;
      i === 0 ? waveCtx.moveTo(0, y) : waveCtx.lineTo(i*step, y);
    });
    waveCtx.stroke();
  }
  frame();
}

function stopWave() {
  if (animFrameId) cancelAnimationFrame(animFrameId);
  waveCtx.clearRect(0,0,waveCanvas.width,waveCanvas.height);
}

function startTimer(el) {
  timerSeconds = 0;
  el.classList.add('visible');
  el.textContent = '00:00';
  timerInterval = setInterval(() => {
    timerSeconds++;
    const m = String(Math.floor(timerSeconds/60)).padStart(2,'0');
    const s = String(timerSeconds%60).padStart(2,'0');
    el.textContent = `${m}:${s}`;
  }, 1000);
}
function stopTimer(el) {
  clearInterval(timerInterval);
  el.classList.remove('visible');
}

async function startRecording(onStop) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(audioChunks, { type: 'audio/webm' });
    onStop(blob);
  };

  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  src.connect(analyser);
  analyserNode = analyser;

  mediaRecorder.start();
  return analyser;
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
}


let soapBlob = null;
let soapRecording = false;

async function toggleSOAPRecording() {
  if (!soapRecording) {
    try {
      const ring = document.getElementById('soap-ring');
      const btn = document.getElementById('soap-mic-btn');
      const label = document.getElementById('soap-rec-label');

      wavePlaceholder.style.display = 'none';
      const analyser = await startRecording(blob => {
        soapBlob = blob;
        document.getElementById('soap-submit-btn').disabled = false;
        document.getElementById('soap-rec-label').textContent = '✅ Recording saved. Click "Generate SOAP Note" to process.';
        stopWave();
        wavePlaceholder.style.display = 'none';
      });

      drawWave(analyser);
      ring.classList.add('recording');
      btn.textContent = '⏹';
      label.textContent = '🔴 Recording… tap to stop';
      startTimer(document.getElementById('soap-timer'));
      soapRecording = true;
    } catch(e) {
      showBanner('soap-banner', 'error', 'Microphone access denied: '+e.message);
    }
  } else {
    stopRecording();
    stopTimer(document.getElementById('soap-timer'));
    document.getElementById('soap-ring').classList.remove('recording');
    document.getElementById('soap-mic-btn').textContent = '🎙️';
    soapRecording = false;
  }
}

async function submitSOAP() {
  if (!soapBlob) return;
  const btn = document.getElementById('soap-submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Generating SOAP Note…';
  hideBanner('soap-banner');

  const form = new FormData();
  form.append('audio', soapBlob, 'recording.webm');

  try {
    const res = await fetch(`${API}/api/soap-from-audio`, { method:'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Server error');

    document.getElementById('soap-transcript').textContent = data.transcription || 'No transcript available.';

    parseAndDisplaySOAP(data.soap || '');

    document.getElementById('soap-results').style.display = 'block';
    document.getElementById('soap-results').scrollIntoView({ behavior:'smooth', block:'start' });
    showBanner('soap-banner', 'success', '✅ SOAP note generated successfully.');
  } catch(e) {
    showBanner('soap-banner', 'error', '❌ ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate SOAP Note';
  }
}

function parseAndDisplaySOAP(text) {
  const sections = { s:'', o:'', a:'', p:'' };
  const patterns = {
    s: /SUBJECTIVE:\s*([\s\S]*?)(?=OBJECTIVE:|ASSESSMENT:|PLAN:|$)/i,
    o: /OBJECTIVE:\s*([\s\S]*?)(?=SUBJECTIVE:|ASSESSMENT:|PLAN:|$)/i,
    a: /ASSESSMENT:\s*([\s\S]*?)(?=SUBJECTIVE:|OBJECTIVE:|PLAN:|$)/i,
    p: /PLAN:\s*([\s\S]*?)(?=SUBJECTIVE:|OBJECTIVE:|ASSESSMENT:|$)/i,
  };
  for (const [k, re] of Object.entries(patterns)) {
    const m = text.match(re);
    sections[k] = m ? m[1].trim() : 'None reported';
  }
  document.getElementById('soap-s').textContent = sections.s;
  document.getElementById('soap-o').textContent = sections.o;
  document.getElementById('soap-a').textContent = sections.a;
  document.getElementById('soap-p').textContent = sections.p;
}


async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendMsg('user', msg);

  const thinking = appendMsg('thinking', '…thinking…');
  document.getElementById('chat-send').disabled = true;

  const form = new FormData();
  form.append('message', msg);

  try {
    const res = await fetch(`${API}/api/agent-chat`, { method:'POST', body: form });
    const data = await res.json();
    thinking.remove();
    if (!res.ok) throw new Error(data.error || 'Server error');
    appendMsg('agent', data.response);
  } catch(e) {
    thinking.remove();
    appendMsg('agent', '⚠️ ' + e.message);
  } finally {
    document.getElementById('chat-send').disabled = false;
    input.focus();
  }
}

function appendMsg(role, text) {
  const box = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

let vcBlob = null;
let vcRecording = false;

async function toggleVoiceChat() {
  if (!vcRecording) {
    try {
      const ring = document.getElementById('vc-ring');
      const btn = document.getElementById('vc-mic-btn');

      const analyser = await startRecording(blob => {
        vcBlob = blob;
        document.getElementById('vc-submit-btn').disabled = false;
        document.getElementById('vc-rec-label').textContent = '✅ Recorded. Click "Send Voice Message".';
      });

      ring.classList.add('recording');
      btn.textContent = '⏹';
      document.getElementById('vc-rec-label').textContent = '🔴 Recording… tap to stop';
      startTimer(document.getElementById('vc-timer'));
      vcRecording = true;
    } catch(e) {
      showBanner('vc-banner', 'error', 'Microphone access denied: '+e.message);
    }
  } else {
    stopRecording();
    stopTimer(document.getElementById('vc-timer'));
    document.getElementById('vc-ring').classList.remove('recording');
    document.getElementById('vc-mic-btn').textContent = '🎙️';
    vcRecording = false;
  }
}

async function submitVoiceChat() {
  if (!vcBlob) return;
  const btn = document.getElementById('vc-submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Processing…';
  hideBanner('vc-banner');

  const form = new FormData();
  form.append('audio', vcBlob, 'voice.webm');

  try {
    const res = await fetch(`${API}/api/voice-chat`, { method:'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Server error');

    document.getElementById('vc-transcription').textContent = data.transcription;
    document.getElementById('vc-text-response').textContent = data.response;

    const audioEl = document.getElementById('vc-audio');
    const bytes = Uint8Array.from(atob(data.audio_b64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type:'audio/mpeg' });
    audioEl.src = URL.createObjectURL(blob);
    audioEl.play();

    document.getElementById('vc-response').classList.add('visible');
    showBanner('vc-banner', 'success', '✅ Response received.');
  } catch(e) {
    showBanner('vc-banner', 'error', '❌ ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Send Voice Message';
  }
}

function showBanner(id, type, msg) {
  const el = document.getElementById(id);
  el.className = 'banner ' + type;
  el.textContent = msg;
}
function hideBanner(id) {
  const el = document.getElementById(id);
  el.className = 'banner';
  el.textContent = '';
}