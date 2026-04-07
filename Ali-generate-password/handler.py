import secrets
import string
import base64
import json
import os
import psycopg2
from datetime import datetime
from io import BytesIO
import qrcode
from cryptography.fernet import Fernet

def handle(req):
    # 1. Extraction du username (T-001)
    try:
        data = json.loads(req)
        username = data.get("username")
    except:
        username = req

    if not username or username == "inconnu":
        return json.dumps({"status": "error", "message": "Username manquant"})

    # 2. Génération du mot de passe (T-002)
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(24))

    # 3. Chiffrement Fernet (T-003)
    # Note : En prod, on utilisera une clé fixe via os.getenv("FERNET_KEY")
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    encrypted_pw = cipher_suite.encrypt(password.encode()).decode()

    # 4. INSERTION EN BASE DE DONNÉES (T-004) ⚙️
    try:
        # On récupère l'URL de connexion (définie plus tard dans K3s/OpenFaaS)
        db_url = os.getenv("POSTGRES_URL", "dbname=cofrap user=postgres password=password host=localhost")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO users (username, password_hash, gendate, expired)
        VALUES (%s, %s, %s, %s);
        """
        cur.execute(insert_query, (username, encrypted_pw, datetime.now(), 0))
        
        conn.commit()
        cur.close()
        conn.close()
        db_status = "Success"
    except Exception as e:
        # Si la DB n'est pas encore connectée, on garde une trace pour le test
        db_status = f"Failed (Normal en test local) : {str(e)}"

    # 5. Génération du QR Code (T-005)
    qr = qrcode.make(password)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    # Réponse finale au Frontend
    return json.dumps({
        "status": "success",
        "user": username,
        "qr_code": qr_base64,
        "db_insertion": db_status,
        "fernet_key_used": key.decode() # À conserver pour déchiffrer plus tard
    })

if __name__ == "__main__":
    print(handle('{"username": "Ali_Test"}'))