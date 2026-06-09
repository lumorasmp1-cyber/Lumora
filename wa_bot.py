import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai
import requests

app = Flask(__name__)

WA_TOKEN = os.environ.get("WA_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "eschaton_verify")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction="Kamu adalah ESCHATON, asisten AI yang cerdas, helpful, dan ramah. Jawab dalam bahasa yang sama dengan user."
)

chat_sessions = {}

def get_session(user_id):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    return chat_sessions[user_id]

def send_wa_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            
            if message["type"] == "text":
                user_text = message["text"]["body"]
                
                if user_text.lower() in ["/start", "halo", "hello", "hi"]:
                    send_wa_message(from_number, "Halo! 👋 Aku ESCHATON, asisten AI siap membantumu.\n\nKetik apa saja untuk mulai chat!\n\nKetik /reset untuk reset percakapan.")
                elif user_text.lower() == "/reset":
                    if from_number in chat_sessions:
                        del chat_sessions[from_number]
                    send_wa_message(from_number, "✅ Percakapan direset!")
                else:
                    session = get_session(from_number)
                    response = session.send_message(user_text)
                    send_wa_message(from_number, response.text)
    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
