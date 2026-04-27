-- init_db.sql mis à jour
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,      -- Stockera le mot de passe de 24 caractères (chiffré) 
    mfa_secret TEXT,                 -- Stockera le secret TOTP (US2) [cite: 71, 80]
    gendate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expired INTEGER DEFAULT 0
);
