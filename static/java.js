// static/app.js
// Frontend logic: speech recognition, fetch to /api/chat, and TTS

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const micBtn = document.getElementById("micBtn");
const sendBtn = document.getElementById("sendBtn");

let recognition = null;
let isListening = false;

// Load saved history (optional)
const historyKey = "flask_voice_chat_history";
let history = JSON.parse(localStorage.getItem(historyKey) || "[]");
history.forEach(h => appendMessage(h.role, h.text));

// Initialize SpeechRecognition if available
if (window.SpeechRecognition || window.webkitSpeechRecognition) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (evt) => {
    const transcript = evt.results[0][0].transcript;
    inputEl.value = transcript;
    setListening(false);
  };

  recognition.onerror = (evt) => {
    console.error("Speech recognition error:", evt.error);
    setListening(false);
  };

  recognition.onend = () => {
    setListening(false);
  };
} else {
  // No SpeechRecognition support
  micBtn.disabled = true;
  micBtn.title = "Microphone not supported in this browser (try Chrome/Edge)";
}

// UI helpers
function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = role === "user" ? "msg user" : "msg assistant";
  wrapper.innerHTML = `<div class="bubble"><pre>${escapeHtml(text)}</pre></div>`;
  chatEl.appendChild(wrapper);
  chatEl.scrollTop = chatEl.scrollHeight;

  // store
  history.push({ role, text });
  localStorage.setItem(historyKey, JSON.stringify(history));
}

function escapeHtml(unsafe) {
  return unsafe
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setListening(flag) {
  isListening = flag;
  micBtn.textContent = flag ? "⏹️" : "🎤";
  micBtn.classList.toggle("listening", flag);
}

// Send message to backend
async function sendMessage(text) {
  if (!text || !text.trim()) return;
  appendMessage("user", text);
  inputEl.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "Sending...";

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      const err = data.error || "Server error";
      appendMessage("assistant", `Error: ${err}`);
      console.error("Server error:", data);
    } else {
      const reply = data.reply || "(no reply)";
      appendMessage("assistant", reply);
      speakText(reply);
    }
  } catch (err) {
    console.error("Network or parsing error:", err);
    appendMessage("assistant", "Network error. See console for details.");
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

// Browser TTS
function speakText(text) {
  if (!("speechSynthesis" in window)) return;
  const utt = new SpeechSynthesisUtterance(text);
  // use default voice / language; app could pick a voice if desired
  window.speechSynthesis.cancel(); // stop any ongoing speech
  window.speechSynthesis.speak(utt);
}

// Form handlers
document.getElementById("controls").addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(inputEl.value);
});

micBtn.addEventListener("click", () => {
  if (!recognition) return;
  if (isListening) {
    recognition.stop();
    setListening(false);
  } else {
    try {
      recognition.start();
      setListening(true);
    } catch (err) {
      console.warn("Could not start recognition:", err);
      setListening(false);
    }
  }
});

// keyboard: Enter sends
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(inputEl.value);
  }
});
