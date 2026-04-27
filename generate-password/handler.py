import secrets
import string
import base64
import json
import os
import re
import psycopg2
from datetime import datetime
from io import BytesIO
import qrcode
import pyotp
from cryptography.fernet import Fernet

# Configuration
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,30}$')

def get_db_connection():
    db_url = os.getenv("POSTGRES_URL", "dbname=cofrap user=postgres password=password host=db port=5432")
    return psycopg2.connect(db_url)

def generate_qr_base64(data):
    """Génère un flux base64 à partir de n'importe quelle donnée (string/URI)"""
    qr = qrcode.make(data)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def generate_complex_password(length=24):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# --- LOGIQUE US1 & US2 ---
def handle_us1_create_account(username):
    password = generate_complex_password(24)
    fernet_key = os.getenv("FERNET_KEY")
    cipher_suite = Fernet(fernet_key.encode())
    enc_password = cipher_suite.encrypt(password.encode()).decode()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return {"status": "error", "message": "Username déjà utilisé"}, 409

    cur.execute(
        "INSERT INTO users (username, password_hash, gendate, expired) VALUES (%s, %s, %s, %s)",
        (username, enc_password, datetime.now(), 0)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "status": "success",
        "qr_code": generate_qr_base64(password),
        "message": "Compte créé. Scannez pour votre mot de passe."
    }, 200

def handle_us2_generate_2fa(username):
    otp_secret = pyotp.random_base32()
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=username, issuer_name="COFRAP-PULSAR")
    
    fernet_key = os.getenv("FERNET_KEY")
    cipher_suite = Fernet(fernet_key.encode())
    enc_mfa = cipher_suite.encrypt(otp_secret.encode()).decode()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET mfa_secret = %s WHERE username = %s", (enc_mfa, username))
    conn.commit()
    cur.close()
    conn.close()

    return {
        "status": "success",
        "qr_code": generate_qr_base64(otp_uri),
        "message": "2FA configurée."
    }, 200

# --- LOGIQUE US3 (AUTHENTIFICATION) ---
def handle_us3_authenticate(username, provided_password, provided_otp):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, mfa_secret, gendate, expired FROM users WHERE username = %s", (username,))
        user_data = cur.fetchone()
        
        if not user_data:
            return {"status": "error", "message": "Utilisateur inconnu"}, 401
        
        db_password_enc, db_mfa_enc, gendate, expired = user_data
        fernet_key = os.getenv("FERNET_KEY")
        cipher_suite = Fernet(fernet_key.encode())

        # Vérification Password
        if provided_password != cipher_suite.decrypt(db_password_enc.encode()).decode():
            return {"status": "error", "message": "Mot de passe incorrect"}, 401

        # Vérification 2FA
        otp_secret = cipher_suite.decrypt(db_mfa_enc.encode()).decode()
        if not pyotp.TOTP(otp_secret).verify(provided_otp):
            return {"status": "error", "message": "Code 2FA invalide"}, 401

        # Vérification Expiration (180 jours)
        if (datetime.now() - gendate).days > 180 or expired == 1:
            return {"status": "expired", "message": "Identifiants expirés"}, 403

        return {"status": "success", "message": "Connexion réussie"}, 200
    finally:
        if 'conn' in locals(): conn.close()

# --- LOGIQUE US4 (RENOUVELLEMENT) ---
def handle_us4_renew(username):
    """Régénère un nouveau couple Password/2FA pour un utilisateur existant"""
    try:
        new_password = generate_complex_password(24)
        new_otp_secret = pyotp.random_base32()
        otp_uri = pyotp.totp.TOTP(new_otp_secret).provisioning_uri(name=username, issuer_name="COFRAP-RENEW")

        fernet_key = os.getenv("FERNET_KEY")
        cipher_suite = Fernet(fernet_key.encode())
        enc_pass = cipher_suite.encrypt(new_password.encode()).decode()
        enc_mfa = cipher_suite.encrypt(new_otp_secret.encode()).decode()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET password_hash = %s, mfa_secret = %s, gendate = %s, expired = 0 
            WHERE username = %s
        """, (enc_pass, enc_mfa, datetime.now(), username))
        conn.commit()
        cur.close()
        conn.close()

        return {
            "status": "success",
            "message": "Nouveaux accès générés.",
            "qr_password": generate_qr_base64(new_password),
            "qr_2fa": generate_qr_base64(otp_uri)
        }, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# --- ROUTEUR PRINCIPAL ---
def handle(req):
    try:
        data = json.loads(req)
        action = data.get("action")
        username = data.get("username")

        if action == "create_account":
            return handle_us1_create_account(username)
        elif action == "setup_2fa":
            return handle_us2_generate_2fa(username)
        elif action == "authenticate":
            return handle_us3_authenticate(username, data.get("password"), data.get("otp"))
        elif action == "renew":
            return handle_us4_renew(username)
        
        return {"status": "error", "message": "Action non reconnue"}, 400
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500