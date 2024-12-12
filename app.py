from flask import Flask, request, jsonify
import requests
import json
import time
from threading import Thread
import schedule
import os

# Configuration de l'application Flask
app = Flask(__name__)

# Tokens et API (récupérés depuis les variables d'environnement)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")  # Token de vérification pour Messenger
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")  # Token d'accès à la page Facebook
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Clé API OpenAI
PAGE_ID = os.getenv("PAGE_ID")  # ID de votre page Facebook pour les posts

if not all([VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, PAGE_ID]):
    raise ValueError("Assurez-vous que toutes les variables d'environnement sont définies : VERIFY_TOKEN, PAGE_ACCESS_TOKEN, OPENAI_API_KEY, PAGE_ID")

# Ajouter une route pour la racine
@app.route("/", methods=["GET"])
def home():
    return "Bienvenue sur le serveur Flask de Clara. Le serveur fonctionne correctement !"

# Fonction pour valider les Webhooks
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge
        return "Token de vérification invalide", 403
    elif request.method == "POST":
        data = request.json
        if data and "entry" in data:
            for entry in data["entry"]:
                for event in entry.get("messaging", []):
                    if "message" in event and "text" in event["message"]:
                        sender_id = event["sender"]["id"]
                        user_message = event["message"]["text"]
                        response_text = generate_response(user_message)
                        send_message(sender_id, response_text)
        return "EVENT_RECEIVED", 200

# Fonction pour envoyer un message via l'API Graph de Facebook
def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v12.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de l'envoi du message : {response.text}")

# Fonction pour générer une réponse via OpenAI
def generate_response(user_message):
    url = "https://api.openai.com/v1/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "text-davinci-003",
        "prompt": f"Utilisateur : {user_message}\nAssistant :",
        "max_tokens": 150,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("text", "Je n'ai pas compris votre demande.")
    else:
        print(f"Erreur avec OpenAI : {response.text}")
        return "Je rencontre un problème technique."

# Fonction pour publier un post sur le mur Facebook
def create_facebook_post(content):
    url = f"https://graph.facebook.com/v12.0/{PAGE_ID}/feed"
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": content,
        "access_token": PAGE_ACCESS_TOKEN
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Post publié avec succès : {content}")
    else:
        print(f"Erreur lors de la publication : {response.text}")

# Fonction pour publier automatiquement deux posts par jour
def schedule_posts():
    posts = [
        "Découvrez les bienfaits de la méditation énergétique pour équilibrer votre esprit et votre corps.",
        "L'énergie positive est contagieuse ! Partagez-la autour de vous dès aujourd'hui."
    ]
    schedule.every().day.at("09:00").do(create_facebook_post, content=posts[0])
    schedule.every().day.at("17:00").do(create_facebook_post, content=posts[1])

    while True:
        schedule.run_pending()
        time.sleep(1)

# Thread pour exécuter les posts programmés
def start_scheduler():
    scheduler_thread = Thread(target=schedule_posts)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# Lancer l'application Flask et le planificateur de posts
if __name__ == "__main__":
    start_scheduler()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
