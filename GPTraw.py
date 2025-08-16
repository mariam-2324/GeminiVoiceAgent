import os
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai

# ---------------------------------------
# 1. Load from .env if not set in OS
# ---------------------------------------
load_dotenv()  # Only loads variables from .env into environment

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError(
        "❌ GOOGLE_API_KEY not found!\n"
        "Set it in your system environment OR create a .env file with:\n"
        "GOOGLE_API_KEY=your_api_key_here"
    )

# ---------------------------------------
# 2. Configure Gemini API
# ---------------------------------------
genai.configure(api_key=API_KEY)
# Updated to use the current stable model
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------------------------------
# 3. Speech-to-Text
# ---------------------------------------
def listen_to_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(f"🗣 You said: {text}")
        return text
    except sr.UnknownValueError:
        print("⚠ Sorry, I could not understand the audio.")
        return ""
    except sr.RequestError as e:
        print(f"⚠ Could not request results; {e}")
        return ""

# ---------------------------------------
# 4. Get AI Response
# ---------------------------------------
def genai_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠ Error generating AI response: {e}")
        return "Sorry, I encountered an error processing your request."

# ---------------------------------------
# 5. Speak Text
# ---------------------------------------
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"⚠ Error with text-to-speech: {e}")

# ---------------------------------------
# 6. Main Loop
# ---------------------------------------
if __name__ == "__main__":
    print("🤖 Voice AI Assistant Started!")
    print("Say 'exit', 'quit', or 'stop' to end the conversation.")
    
    while True:
        user_input = listen_to_audio()
        if user_input.lower() in ["exit", "quit", "stop"]:
            print("👋 Exiting...")
            break
        if user_input.strip():
            ai_output = genai_response(user_input)
            print(f"🤖 AI: {ai_output}")
            speak_text(ai_output)