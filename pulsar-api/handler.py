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

USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,30}$')

def get_db_connection():
    # Connexion DNS interne au cluster Kubernetes
    db_url = os.getenv("POSTGRES_URL", "dbname=cofrap user=postgres password=password host=postgres-service.default.svc.cluster.local port=5432")
    return psycopg2.connect(db_url)

def get_fernet_key():
    # Lecture sécurisée du Secret Kubernetes monté par OpenFaaS
    secret_path = "/var/openfaas/secrets/fernet-key"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()
    return os.getenv("FERNET_KEY", "")

def generate_qr_base64(data):
    qr = qrcode.make(data)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def generate_complex_password(length=24):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# --- LOGIQUE US1 ---
def handle_us1_create_account(username):
    password = generate_complex_password(24)
    fernet_key = get_fernet_key()
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

# --- LOGIQUE US2 ---
def handle_us2_generate_2fa(username):
    otp_secret = pyotp.random_base32()
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=username, issuer_name="COFRAP-PULSAR")
    
    fernet_key = get_fernet_key()
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

# --- LOGIQUE US3 ---    
def handle_us3_authenticate(username, provided_password, provided_otp):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, mfa_secret, gendate, expired FROM users WHERE username = %s", (username,))
        user_data = cur.fetchone()
        
        if not user_data:
            return {"status": "error", "message": "Utilisateur inconnu"}, 401
        
        db_password_enc, db_mfa_enc, gendate, expired = user_data
        fernet_key = get_fernet_key()
        cipher_suite = Fernet(fernet_key.encode())

        if provided_password != cipher_suite.decrypt(db_password_enc.encode()).decode():
            return {"status": "error", "message": "Mot de passe incorrect"}, 401

        otp_secret = cipher_suite.decrypt(db_mfa_enc.encode()).decode()
        if not pyotp.TOTP(otp_secret).verify(provided_otp):
            return {"status": "error", "message": "Code 2FA invalide"}, 401

        if (datetime.now() - gendate).days > 180 or expired == 1:
            return {"status": "expired", "message": "Identifiants expirés"}, 403

        return {"status": "success", "message": "Connexion réussie"}, 200
    finally:
        if 'conn' in locals(): conn.close()

# --- LOGIQUE US4 ---
def handle_us4_renew(username):
    try:
        new_password = generate_complex_password(24)
        new_otp_secret = pyotp.random_base32()
        otp_uri = pyotp.totp.TOTP(new_otp_secret).provisioning_uri(name=username, issuer_name="COFRAP-RENEW")

        fernet_key = get_fernet_key()
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

# --- POINT D'ENTRÉE NATIF OPENFAAS ---
def handle(event, context):
    # En-têtes obligatoires pour gérer les appels CORS depuis le Frontend
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    # Intercepter les requêtes de pré-vérification CORS des navigateurs
    if event.method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        data = json.loads(event.body.decode('utf-8'))
        action = data.get("action")
        username = data.get("username")

        if action == "create_account":
            response_body, status_code = handle_us1_create_account(username)
        elif action == "setup_2fa":
            response_body, status_code = handle_us2_generate_2fa(username)
        elif action == "authenticate":
            response_body, status_code = handle_us3_authenticate(username, data.get("password"), data.get("otp"))
        elif action == "renew":
            response_body, status_code = handle_us4_renew(username)
        else:
            response_body, status_code = {"status": "error", "message": "Action non reconnue"}, 400

        return {
            "statusCode": status_code,
            "headers": cors_headers,
            "body": json.dumps(response_body)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"status": "error", "message": str(e)})
        }