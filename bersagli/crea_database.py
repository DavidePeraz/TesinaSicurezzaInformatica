r"""
============================================================================
Generatore del database PERSISTENTE (file su disco) - dati.db
============================================================================
A differenza dei bersagli con DB in memoria, qui creiamo un vero file
`dati.db` (SQLite) che si puo' ISPEZIONARE con strumenti come
"DB Browser for SQLite" e mostrare nella tesi.

Contiene:
  - `informazioni_pubbliche` : dati che un utente normale puo' vedere;
  - `informazioni_riservate` : dati sensibili (con la flag), da proteggere;
  - `utenti`                 : credenziali per il login (admin + utente normale).

Esegui una volta:  .\.venv\Scripts\python.exe bersagli\crea_database.py
Poi apri `bersagli\dati.db` per vederne il contenuto.
============================================================================
"""

import os
import secrets
import sqlite3
import string

# Il file .db viene creato ACCANTO a questo script (non dipende da dove lo lanci).
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati.db")

FLAG = "FLAG_DB{TESI_RISERVATO_2026}"


def genera_password_complessa(lunghezza: int = 16) -> str:
    alfabeto = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alfabeto) for _ in range(lunghezza))


def crea() -> None:
    # Ricreiamo il file da zero ad ogni esecuzione (ambiente riproducibile).
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # --- Tabella PUBBLICA: visibile a un utente normale ---
    cur.execute(
        "CREATE TABLE informazioni_pubbliche (id INTEGER PRIMARY KEY, titolo TEXT, contenuto TEXT)"
    )
    cur.executemany(
        "INSERT INTO informazioni_pubbliche (titolo, contenuto) VALUES (?, ?)",
        [
            ("Orari ufficio", "Lun-Ven 9:00-18:00"),
            ("Sede", "Via Roma 1, Milano"),
            ("Contatti", "info@azienda-esempio.it"),
            ("Novita'", "Nuovo catalogo prodotti disponibile online"),
        ],
    )

    # --- Tabella RISERVATA: dati sensibili, con la flag ---
    cur.execute(
        "CREATE TABLE informazioni_riservate (id INTEGER PRIMARY KEY, titolo TEXT, contenuto TEXT)"
    )
    cur.executemany(
        "INSERT INTO informazioni_riservate (titolo, contenuto) VALUES (?, ?)",
        [
            ("Fatturato Q4", "1.240.000 EUR (riservato)"),
            ("Stipendi dirigenti", "CEO 180k, CTO 150k (riservato)"),
            ("Password server", "root: Xy9!server-2026"),
            ("FLAG", FLAG),
        ],
    )

    # --- Tabella UTENTI: per il login ---
    cur.execute(
        "CREATE TABLE utenti (id INTEGER PRIMARY KEY, username TEXT, password TEXT, is_admin INTEGER)"
    )
    pwd_admin = genera_password_complessa()
    cur.executemany(
        "INSERT INTO utenti (username, password, is_admin) VALUES (?, ?, ?)",
        [
            ("admin", pwd_admin, 1),
            ("mario", "mario123", 0),  # utente normale
        ],
    )

    conn.commit()
    conn.close()

    print("=" * 60)
    print(f"[OK] Database creato: {DB_FILE}")
    print(f"     Credenziali admin legittime -> admin : {pwd_admin}")
    print(f"     Utente normale               -> mario : mario123")
    print("     Tabelle: informazioni_pubbliche, informazioni_riservate, utenti")
    print("=" * 60)


if __name__ == "__main__":
    crea()
