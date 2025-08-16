
"""
Single-file Flask app that serves:
 - a minimal HTML + JS frontend (Web Speech API used in browser)
 - a POST /api/chat endpoint that calls Google Gemini via google.generativeai
Features:
 - Safe fallbacks: if GOOGLE_API_KEY is missing or USE_MOCK=1, the server uses a mock reply (for local testing).
 - Robust response extraction from the SDK object.
"""

import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string

# Load .env if present
load_dotenv()

# Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
USE_MOCK = os.getenv("USE_MOCK", "0").lower() in ("1", "true", "yes")
DEBUG = os.getenv("DEBUG", "1").lower() in ("1", "true", "yes")

# Try to import Google generative SDK; allow app to run in mock mode if import fails.
genai = None
model = None
if not USE_MOCK:
    try:
        import google.generativeai as genai
        if API_KEY:
            genai.configure(api_key=API_KEY)
            # Choose the model name you have access to; keep gemini-pro if you have access
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
            except Exception:
                # fallback to a more stable/common model name if available in your SDK
                try:
                    model = genai.GenerativeModel("gemini-1.5")
                except Exception:
                    model = None
        else:
            # No API key: force mock mode
            USE_MOCK = True
    except Exception as e:
        # If import fails, fall back to mock mode but log for debugging
        print("Warning: google.generativeai import failed or initialization failed:", str(e))
        USE_MOCK = True

app = Flask(__name__)


# Simple HTML/JS served from here (so it's a single-file app). You can replace with templates if preferred.
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Flask Gemini Voice Chatbot</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <style>
    body{font-family:Inter,system-ui,Arial;margin:20px;background:#006666;color:#ff758f}
    .container{max-width:900px;margin:0 auto}
    header{display:flex;justify-content:space-between;align-items:center}
    .chat{min-height:380px;max-height:60vh;overflow:auto;background:#66b2b2;padding:12px;border-radius:10px;border:1px solid #e6e9f2}
    .msg{margin:8px 0;display:flex}
    .msg.user{justify-content:flex-end}
    .bubble{padding:10px 12px;border-radius:12px;max-width:78%;white-space:pre-wrap;background:#a0d6b4}
    .msg.user .bubble{background:#A0A6BE;color:white}
    .controls{display:flex;gap:8px;margin-top:12px}
    input[type="text"]{flex:1;padding:10px;border-radius:8px;border:1px solid #d1d5db}
    button{padding:10px 14px;border-radius:8px;border:1px solid #d1d5db;background:#004c4c;cursor:pointer}
    button:disabled{opacity:.6;cursor:not-allowed}
    .muted{color:#ff758f;font-size:13px;margin-top:8px}
    .listening{background:#ff758f !important}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>🤖 Gemini Voice Chatbot</h1>
    <div><small>Mock mode: <strong id="mockFlag">UNKNOWN</strong></small></div>
  </header>

  <div id="chat" class="chat" aria-live="polite"></div>

  <form id="controls" class="controls">
    <input id="input" type="text" placeholder="Type a message or use the mic..." autocomplete="off" />
    <button id="micBtn" type="button" title="Use microphone">🎤</button>
    <button id="sendBtn" type="submit">Send</button>
  </form>

  <div class="muted">Uses the browser Web Speech API for voice I/O. Best in Chrome/Edge.</div>
</div>

<script>
(function(){
  const chatEl = document.getElementById('chat');
  const inputEl = document.getElementById('input');
  const micBtn = document.getElementById('micBtn');
  const sendBtn = document.getElementById('sendBtn');
  const mockFlagEl = document.getElementById('mockFlag');

  // Set mock flag text from server-rendered variable
  const USING_MOCK = {{ use_mock | lower }};
  mockFlagEl.textContent = USING_MOCK ? 'ON' : 'OFF';

  function append(role, text){
    const wrapper = document.createElement('div');
    wrapper.className = 'msg ' + (role === 'user' ? 'user' : 'assistant');
    const b = document.createElement('div');
    b.className = 'bubble';
    b.innerText = text;
    wrapper.appendChild(b);
    chatEl.appendChild(wrapper);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  async function sendMessage(text){
    if(!text || !text.trim()) return;
    append('user', text);
    inputEl.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text})
      });
      const data = await res.json();
      if(!res.ok){
        append('assistant', 'Error: ' + (data.error || 'Server error'));
      } else {
        const reply = data.reply || '(no reply)';
        append('assistant', reply);
        // Speak reply
        if('speechSynthesis' in window){
          const utt = new SpeechSynthesisUtterance(reply);
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(utt);
        }
      }
    } catch(err){
      console.error(err);
      append('assistant', 'Network error. See console.');
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Send';
    }
  }

  // Form submit
  document.getElementById('controls').addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage(inputEl.value);
  });

  // SpeechRecognition
  let recognition = null;
  let listening = false;
  if(window.SpeechRecognition || window.webkitSpeechRecognition){
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (evt) => {
      const t = evt.results[0][0].transcript;
      inputEl.value = t;
      listening = false;
      micBtn.classList.remove('listening');
    };
    recognition.onend = () => {
      listening = false;
      micBtn.classList.remove('listening');
    };
    recognition.onerror = (e) => {
      console.error('Rec error', e);
      listening = false;
      micBtn.classList.remove('listening');
    };
  } else {
    micBtn.disabled = true;
    micBtn.title = 'SpeechRecognition not supported in this browser (try Chrome/Edge)';
  }

    micBtn.addEventListener('click', () => {
    if(!recognition) return;
    if(listening){
      recognition.stop();
      listening = false;
      micBtn.classList.remove('listening');
    } else {
      try {
        recognition.start();
        listening = true;
        micBtn.classList.add('listening');
      } catch(err){
        console.warn('Could not start recognition', err);
      }
    }
  });

  // Keyboard: Enter to send
  inputEl.addEventListener('keydown', (e) => {
    if(e.key === 'Enter' && !e.shiftKey){
      e.preventDefault();
      sendMessage(inputEl.value);
    }
  });

  // Welcome message
  append('assistant', 'Hello — I am your voice assistant. Say or type something.');
})();
</script>
</body>
</html>
"""

def extract_text_from_response(resp):
    """
    Try common attributes / shapes returned by google.generativeai SDK objects.
    Return a text string for the reply; never raise here.
    """
    try:
        if resp is None:
            return None
        # If it's already a string
        if isinstance(resp, str):
            return resp
        # If object has .text property (common)
        text = getattr(resp, "text", None)
        if text:
            return text
        # Try candidates -> content -> text
        candidates = getattr(resp, "candidates", None)
        if candidates:
            try:
                first = candidates[0]
                # Some SDK versions have first.output_text
                if hasattr(first, "output_text"):
                    return first.output_text
                # Some nested structures: first.content is list with dicts containing text
                content = getattr(first, "content", None)
                if content:
                    # if content is a list of dicts or strings
                    if isinstance(content, (list, tuple)) and len(content) > 0:
                        c0 = content[0]
                        # object with .text
                        if hasattr(c0, "text"):
                            return c0.text
                        # dict with 'text'
                        if isinstance(c0, dict) and "text" in c0:
                            return c0["text"]
                        # string
                        if isinstance(c0, str):
                            return c0
            except Exception:
                pass
        # Try mapping-like shapes
        if isinstance(resp, dict):
            # candidates -> first -> output_text or content
            if "candidates" in resp and resp["candidates"]:
                cand = resp["candidates"][0]
                if isinstance(cand, dict):
                    if "output_text" in cand:
                        return cand["output_text"]
                    if "content" in cand and isinstance(cand["content"], list) and cand["content"]:
                        c0 = cand["content"][0]
                        if isinstance(c0, dict) and "text" in c0:
                            return c0["text"]
                        if isinstance(c0, str):
                            return c0
        # last resort: string representation
        return str(resp)
    except Exception:
        try:
            return str(resp)
        except Exception:
            return "(unable to extract text)"

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, use_mock=str(USE_MOCK).lower())

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field."}), 400
    user_message = data["message"]

    if not user_message or not str(user_message).strip():
        return jsonify({"error": "Empty message."}), 400

    # Mock mode for local testing
    if USE_MOCK:
        reply = f"(mock) I received: {user_message}"
        return jsonify({"reply": reply})

    # Real call to Google Generative AI
    try:
        if model is None:
            return jsonify({"error": "Model not initialized. Check server logs and API key."}), 500

        # model.generate_content may accept a string or more complex input depending on SDK version
        resp = model.generate_content(user_message)
        reply_text = extract_text_from_response(resp)
        return jsonify({"reply": reply_text})
    except Exception as e:
        # In debug show error message; in production hide details
        msg = str(e) if DEBUG else "Model error"
        return jsonify({"error": msg}), 500


if __name__ == "__main__":
    # Important: ensure this file is NOT named flask.py to avoid shadowing the real flask package.
    print(f"Starting Flask app (USE_MOCK={USE_MOCK}). DEBUG={DEBUG}")
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
