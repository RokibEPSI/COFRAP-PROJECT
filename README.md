# COFRAP Project

COFRAP est une application de demonstration autour de la gestion d'acces securises. Le projet permet de creer un compte, generer un mot de passe complexe, configurer une authentification a deux facteurs via QR code, verifier une connexion, puis renouveler les acces en cas d'expiration.

Le projet est compose de trois briques principales :

- un backend Python/Flask qui expose les actions metier
- une base PostgreSQL qui stocke les donnees chiffrees
- un frontend HTML/CSS/JavaScript qui pilote les parcours utilisateur

## Vue d'ensemble

L'application couvre aujourd'hui quatre parcours principaux :

- `US1 - Creation de compte` : generation d'un mot de passe de 24 caracteres, chiffrement Fernet, stockage en base, puis exposition du mot de passe via un QR code
- `US2 - Activation 2FA` : generation d'un secret TOTP, chiffrement, stockage en base, puis affichage d'un QR code compatible application d'authentification
- `US3 - Authentification` : verification du mot de passe, du code OTP et de l'expiration des identifiants
- `US4 - Renouvellement` : regeneration d'un nouveau mot de passe et d'un nouveau secret 2FA

Le frontend consomme un endpoint unique :

- `POST /function/generate-password`

Le backend differencie ensuite les traitements via un champ `action` dans le JSON recu.

## Fonctionnalites

- Generation d'un mot de passe complexe de 24 caracteres
- Chiffrement des secrets avec `Fernet`
- Stockage des utilisateurs dans PostgreSQL
- Generation de QR codes en Base64
- Configuration 2FA via `pyotp`
- Verification de la validite des acces
- Renouvellement automatique des acces expires
- Interface web simple pour inscription et connexion

## Architecture Technique

### Backend

Le backend est ecrit en Python avec Flask. Il expose une route HTTP unique qui sert de point d'entree aux actions metier.

Fichiers principaux :

- [generate-password/app.py](/d:/EPSI/mspr2/COFRAP-PROJECT/generate-password/app.py)
- [generate-password/handler.py](/d:/EPSI/mspr2/COFRAP-PROJECT/generate-password/handler.py)

Le backend s'appuie sur :

- `Flask` pour l'API HTTP
- `psycopg2-binary` pour PostgreSQL
- `cryptography` pour Fernet
- `qrcode` pour les QR codes
- `pyotp` pour la generation et la verification TOTP

### Base de donnees

La base de donnees utilise PostgreSQL.

Le schema initial est defini dans :

- [init_db.sql](/d:/EPSI/mspr2/COFRAP-PROJECT/init_db.sql)

La table `users` stocke notamment :

- `username`
- `password_hash` : mot de passe chiffre
- `mfa_secret` : secret TOTP chiffre
- `gendate` : date de generation
- `expired` : indicateur d'expiration

### Frontend

Le frontend est une page statique servie par Nginx.

Fichier principal :

- [frontend/index.html](/d:/EPSI/mspr2/COFRAP-PROJECT/frontend/index.html)

Il fournit :

- un ecran d'inscription
- un ecran de connexion
- l'affichage des QR codes
- la gestion des messages d'erreur et de succes

### Conteneurisation

Le projet peut etre lance localement avec Docker Compose via :

- [docker-compose.yml](/d:/EPSI/mspr2/COFRAP-PROJECT/docker-compose.yml)

Les services definis sont :

- `db` : PostgreSQL 15
- `backend` : API Python/Flask
- `frontend` : Nginx servant l'interface

### OpenFaaS

Un fichier [stack.yml](/d:/EPSI/mspr2/COFRAP-PROJECT/stack.yml) est present dans le depot. Il montre l'intention de deploiement OpenFaaS, mais il n'est pas encore totalement aligne avec l'arborescence actuelle du projet. Le mode d'execution le plus fiable aujourd'hui reste Docker Compose.

## Prerequis

### Pour Docker

- Docker Desktop ou Docker Engine
- Docker Compose

### Pour un lancement local sans Docker

- Python 3.11 ou plus
- PostgreSQL 15 ou equivalent
- `pip`

## Installation & Demarrage (Docker)

Depuis la racine du projet :

```powershell
docker compose up --build
```

Une fois les services demarres :

- frontend : `http://localhost`
- backend : `http://localhost:8080`
- PostgreSQL : `localhost:5433`

Le port PostgreSQL expose est `5433` cote machine hote pour eviter les conflits avec une installation locale deja presente sur `5432`.

### Arret des services

```powershell
docker compose down
```

### Reinitialiser les volumes de base de donnees

```powershell
docker compose down -v
```

Utilise cette commande uniquement si tu veux repartir d'une base vide.

## Variables d'environnement

Le backend utilise principalement deux variables :

- `POSTGRES_URL`
- `FERNET_KEY`

Valeurs actuellement configurees dans Docker Compose :

- `POSTGRES_URL=dbname=cofrap user=postgres password=password host=db port=5432`
- `FERNET_KEY=<cle fernet>`

En dehors d'un contexte de demonstration, ces valeurs ne doivent pas etre versionnees en clair.

## Developpement local sans Docker

### 1. Creer la base PostgreSQL

Creer une base `cofrap`, puis executer le script SQL :

```powershell
psql -U postgres -d cofrap -f init_db.sql
```

### 2. Installer les dependances Python

Depuis le dossier `generate-password` :

```powershell
pip install -r requirements.txt
```

### 3. Definir les variables d'environnement

Exemple PowerShell :

```powershell
$env:POSTGRES_URL="dbname=cofrap user=postgres password=password host=localhost port=5432"
$env:FERNET_KEY="QJ1pAcr4N9EqFg4uZzJCte4YbE5Z-Cez-DkUZwosLBo="
```

### 4. Lancer le backend

Toujours depuis `generate-password` :

```powershell
python app.py
```

Le backend sera disponible sur :

- `http://localhost:8080/function/generate-password`

### 5. Lancer le frontend

Le frontend etant statique, plusieurs options sont possibles :

- ouvrir `frontend/index.html` dans un navigateur
- ou servir le dossier avec un petit serveur web local

Exemple avec Python :

```powershell
cd frontend
python -m http.server 8081
```

Puis ouvrir :

- `http://localhost:8081`

## Exemple d'appels API

### Creer un compte

```json
{
  "action": "create_account",
  "username": "alice"
}
```

### Configurer la 2FA

```json
{
  "action": "setup_2fa",
  "username": "alice"
}
```

### Authentifier un utilisateur

```json
{
  "action": "authenticate",
  "username": "alice",
  "password": "motdepasse",
  "otp": "123456"
}
```

### Renouveler les acces

```json
{
  "action": "renew",
  "username": "alice"
}
```

## Structure du Projet

```text
COFRAP-PROJECT/
├── generate-password/
│   ├── app.py
│   ├── handler.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── Dockerfile
├── function/
│   └── authenticate-user/
├── infra/
├── docker-compose.yml
├── init_db.sql
├── README.md
└── stack.yml
```

## Securite

Le projet integre deja plusieurs mecanismes utiles pour une demonstration securisee :

- chiffrement des mots de passe et secrets TOTP avec `Fernet`
- mot de passe genere aleatoirement avec `secrets`
- 2FA basee sur TOTP
- verification d'expiration des identifiants

Quelques limites a garder en tete :

- les secrets sont encore presents en clair dans `docker-compose.yml`
- le backend expose actuellement un endpoint unique pour plusieurs actions
- certaines validations d'entree pourraient etre renforcees
- il n'y a pas encore de gestion fine des journaux, de rate limiting ou de traçabilite complete

Pour une mise en production, il faudrait au minimum :

- externaliser les secrets
- durcir la validation des entrees
- ajouter des tests automatises
- revoir la strategie de rotation et d'expiration
- aligner le deploiement OpenFaaS/Kubernetes avec le code reel

## Points d'attention

- Le dossier `infra/` est actuellement vide.
- Le fichier `stack.yml` ne reflète pas encore exactement la structure executable du projet.
- Le dossier `function/authenticate-user/` est present, mais n'est pas integre au flux principal visible via Docker Compose.
- L'encodage de certains anciens fichiers a pu etre degrade ; le `README` a ete re-ecrit proprement pour servir de reference centrale.

## Pistes d'amelioration

- ajouter des tests unitaires et d'integration
- separer les routes selon les usages metier
- ajouter une vraie gestion des erreurs cote frontend
- fournir un `.env.example`
- preparer un deploiement Kubernetes ou OpenFaaS complet et teste
- documenter les parcours utilisateurs avec captures ou schemas



