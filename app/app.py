import html
import os

from flask import Flask, jsonify

app = Flask(__name__)


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development")


def get_app_message() -> str:
    return os.getenv("APP_MESSAGE", "Application Flask opérationnelle.")


@app.get("/")
def home():
    app_env = html.escape(get_app_env())
    message = html.escape(get_app_message())
    api_key_configured = bool(os.getenv("API_KEY"))

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kubernetes Orchestration - Flask</title>
</head>
<body>
  <main>
    <h1>Projet fil rouge Kubernetes</h1>
    <p>{message}</p>
    <dl>
      <dt>Environnement</dt><dd>{app_env}</dd>
      <dt>Clé API configurée</dt><dd>{"oui" if api_key_configured else "non"}</dd>
    </dl>
    <p>Routes de vérification : <code>/health</code> et <code>/ready</code>.</p>
  </main>
</body>
</html>"""


@app.get("/health")
def health():
    """Liveness probe : le processus HTTP répond."""
    return jsonify(status="ok"), 200


@app.get("/ready")
def ready():
    """Readiness probe : l'application peut recevoir du trafic."""
    return jsonify(status="ready"), 200


if __name__ == "__main__":
    # Le serveur intégré de Flask suffit pour ce lab de formation uniquement.
    app.run(host="0.0.0.0", port=5000)
