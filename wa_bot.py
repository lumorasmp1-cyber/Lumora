import os
import json
from flask import Flask, request, jsonify
from groq import Groq
import requests

app = Flask(__name__)

WA_TOKEN = os.environ.get("WA_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "eschaton_verify")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = "Kamu adalah LUMORA, asisten AI yang cerdas, helpful, dan ramah. Jawab dalam bahasa yang sama dengan user. Kalau user pakai Bahasa Indonesia, jawab Indonesia. Kalau Inggris, jawab Inggris. Jadilah natural dan membantu."

chat_histories = {}

def get_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

def ask_groq(user_id, user_message):
    history = get_history(user_id)
    history.append({"role": "user", "content": user_message})
    if len(history) > 20:
        history = history[-20:]
        chat_histories[user_id] = history

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000
    )
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

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
                    send_wa_message(from_number, "Halo! 👋 Aku LUMORA, asisten AI siap membantumu.\n\nKetik apa saja untuk mulai chat!\n\nKetik /reset untuk reset percakapan.")
                elif user_text.lower() == "/reset":
                    chat_histories[from_number] = []
                    send_wa_message(from_number, "✅ Percakapan direset!")
                else:
                    reply = ask_groq(from_number, user_text)
                    send_wa_message(from_number, reply)
    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
