import secrets
import string
import random
import base64
import json
import os
import re
import psycopg2
import psycopg2.errorcodes
from datetime import datetime
from io import BytesIO
import qrcode
import pyotp
from cryptography.fernet import Fernet

USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,30}$')


def validate_username(username):
    if not username or not isinstance(username, str):
        return "Username manquant"

    username = username.strip()
    if len(username) < 3:
        return "Username trop court (minimum 3 caractères)"
    if len(username) > 30:
        return "Username trop long (maximum 30 caractères)"
    if not USERNAME_PATTERN.fullmatch(username):
        return "Username invalide : uniquement lettres, chiffres, tirets et underscores autorisés"

    return None


def generate_otp_secret():
    """Génère une clé secrète OTP valide (base32)"""
    return pyotp.random_base32()


def handle(req):
    try:
        data = json.loads(req)
    except Exception:
        return {"status": "error", "message": "JSON invalide"}, 400

    username = data.get("username")
    validation_error = validate_username(username)
    if validation_error:
        return {"status": "error", "message": validation_error}, 400

    # Générer une clé secrète OTP
    otp_secret = generate_otp_secret()

    # Créer l'URI OTP au format standard pour les authenticators
    totp = pyotp.TOTP(otp_secret)
    otp_uri = totp.provisioning_uri(
        name=username,
        issuer_name='COFRAP'
    )

    fernet_key = os.getenv("FERNET_KEY")
    if fernet_key is None:
        return {"status": "error", "message": "FERNET_KEY non défini"}, 500

    cipher_suite = Fernet(fernet_key.encode())
    encrypted_secret = cipher_suite.encrypt(otp_secret.encode()).decode()

    try:
        db_url = os.getenv("POSTGRES_URL", "dbname=cofrap user=postgres password=password host=localhost")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return {"status": "error", "message": "Username déjà utilisé"}, 409

        insert_query = """
        INSERT INTO users (username, password_hash, gendate, expired)
        VALUES (%s, %s, %s, %s);
        """
        cur.execute(insert_query, (username, encrypted_secret, datetime.now(), 0))
        conn.commit()
        cur.close()
        conn.close()

    except psycopg2.IntegrityError as e:
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        if getattr(e, 'pgcode', None) == psycopg2.errorcodes.UNIQUE_VIOLATION:
            return {"status": "error", "message": "Username déjà utilisé"}, 409
        return {"status": "error", "message": "Erreur base de données"}, 500

    except Exception as e:
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except Exception:
                pass
        return {"status": "error", "message": str(e)}, 500

    # Générer le QR code à partir de l'URI OTP (pas du mot de passe)
    qr = qrcode.make(otp_uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {
        "status": "success",
        "user": username,
        "qr_code": qr_base64,
        "otp_uri": otp_uri,
        "db_insertion": "Success"
    }, 200


if __name__ == "__main__":
    response, status = handle('{"username": "Ali_Test"}')
    print(status, response)