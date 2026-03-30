import secrets
import string
import base64
import json
from io import BytesIO
import qrcode
from cryptography.fernet import Fernet

def handle(req):
    """
    Entrée : JSON avec {"username": "nom"}
    Sortie : JSON avec QR Code et Confirmation
    """
    # Extraction du username
    try:
        data = json.loads(req)
        username = data.get("username", "inconnu")
    except:
        username = req # Si c'est du texte brut

    # --- T-002 : Mot de passe 24 caractères ---
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(24))

    # --- T-003 : Chiffrement Fernet (AES) ---
    # On génère une clé de test (En prod elle sera fixe dans un secret)
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    encrypted_pw = cipher_suite.encrypt(password.encode()).decode()

    # --- T-005 : Génération du QR Code ---
    qr = qrcode.make(password)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    # Réponse JSON pour le Frontend
    return json.dumps({
        "status": "success",
        "user": username,
        "qr_code": qr_base64,
        "debug_pw_encrypted": encrypted_pw # Ce qu'on enverra en DB (T-004)
    })
    # Ce bloc dit à Python d'exécuter la fonction quand on lance le script
if __name__ == "__main__":
    print(handle('{"username": "Ali_Test"}'))