import threading
import time

import requests
from flask import Flask

from constants import KOYEB_PUBLIC_LINK

app = Flask(__name__)


@app.route('/keep_alive')
def keep_alive():
    return "I'm alive!"


def ping_bot():
    while True:
        try:
            requests.get(f'{KOYEB_PUBLIC_LINK}/keep_alive')
        except requests.exceptions.RequestException as e:
            print(f"Keep-alive request failed: {e}")
        time.sleep(300)  # Ping every 5 minutes


def run_flask():
    app.run(host='0.0.0.0', port=8000)


def start_flask():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    keep_alive_thread = threading.Thread(target=ping_bot, daemon=True)
    keep_alive_thread.start()
