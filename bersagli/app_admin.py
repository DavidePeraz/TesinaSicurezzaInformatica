"""
============================================================================
BERSAGLIO DIDATTICO #3 - Attacco CONCATENATO
  Auth bypass (SQLi) -> sessione admin -> accesso ad area riservata
============================================================================
Unisce i due scenari precedenti in una catena realistica:
  1) il login (`/`) e' vulnerabile a SQL Injection -> auth bypass;
  2) al login riuscito il server rilascia una SESSIONE con ruolo admin;
  3) l'area riservata (`/pannello`) mostra dati sensibili SOLO a chi ha una
     sessione admin valida -> senza login legittimo/bypass restituisce 403.

Obiettivo dell'attaccante: entrare come admin sfruttando la SQLi e, con i
privilegi ottenuti, leggere i dati riservati (la flag) nel pannello.

ATTENZIONE: codice INTENZIONALMENTE VULNERABILE, solo per sandbox isolata.
Gira sulla porta 8080 (come gli altri bersagli): UN bersaglio alla volta.
============================================================================
"""

import secrets
import sqlite3
import string

from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)
# Chiave per firmare i cookie di sessione (casuale ad ogni avvio).
app.secret_key = secrets.token_hex(16)

DB_PATH = "file:admin_db?mode=memory&cache=shared"

# La flag e' un DATO RISERVATO, visibile solo dal pannello admin.
FLAG = "FLAG_ADMIN{TESI_PRIVILEGE_2026}"

_keepalive_conn = None


def genera_password_complessa(lunghezza: int = 20) -> str:
    alfabeto = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alfabeto) for _ in range(lunghezza))


def init_db() -> None:
    global _keepalive_conn
    _keepalive_conn = sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)
    cur = _keepalive_conn.cursor()
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, is_admin INTEGER)"
    )
    pwd_admin = genera_password_complessa()
    cur.executemany(
        "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        [
            ("admin", pwd_admin, 1),
            ("mario", "mario123", 0),  # utente normale, NON admin
        ],
    )
    _keepalive_conn.commit()
    print("=" * 60)
    print("[SANDBOX] Bersaglio #3 (login + area riservata) inizializzato.")
    print(f"[SANDBOX] Credenziali admin legittime -> admin : {pwd_admin}")
    print("=" * 60)


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)


PAGINA_LOGIN = """
<!doctype html>
<html lang="it">
<head><meta charset="utf-8"><title>Bersaglio #3 - Login</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 60px auto; padding: 0 16px; }}
 form {{ display: flex; flex-direction: column; gap: 10px; }}
 input {{ padding: 8px; }} button {{ padding: 10px; cursor: pointer; }}
 .box {{ margin-top: 20px; padding: 14px; border-radius: 6px; }}
 .ok {{ background: #e6ffed; border: 1px solid #34d058; }}
 .err {{ background: #ffeef0; border: 1px solid #d73a49; font-family: monospace; white-space: pre-wrap; }}
</style></head>
<body>
 <h1>Area riservata &mdash; Login</h1>
 <form method="post" action="/">
   <input type="text" name="username" placeholder="Username" autofocus>
   <input type="text" name="password" placeholder="Password">
   <button type="submit">Accedi</button>
 </form>
 {risultato}
</body></html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    risultato = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_connection()
        cur = conn.cursor()
        try:
            # ================================================================
            # >>> VULNERABILITA' SQL INJECTION (auth bypass) - RIGA CRITICA <<<
            # Input concatenato: `admin' --` bypassa il controllo password.
            # ================================================================
            query = (
                "SELECT username, is_admin FROM users WHERE username = '"
                + username
                + "' AND password = '"
                + password
                + "'"
            )
            cur.execute(query)
            utente = cur.fetchone()
            if utente:
                # Login riuscito: rilascio la SESSIONE (cookie firmato).
                session["logged_in"] = True
                session["username"] = utente[0]
                session["is_admin"] = bool(utente[1])
                risultato = (
                    '<div class="box ok">Accesso effettuato come '
                    f"<b>{utente[0]}</b>. I dati riservati sono nel "
                    '<a href="/pannello">pannello amministratore</a>.</div>'
                )
            else:
                risultato = '<div class="box err">Credenziali non valide.</div>'
        except sqlite3.Error as e:
            risultato = f'<div class="box err">Errore SQL: {e}</div>'
        finally:
            conn.close()
    return PAGINA_LOGIN.format(risultato=risultato)


@app.route("/pannello")
def pannello():
    # CONTROLLO DI AUTORIZZAZIONE: senza sessione admin -> 403.
    if not session.get("logged_in") or not session.get("is_admin"):
        return (
            "<h1>403 - Accesso negato</h1>"
            "<p>Devi essere autenticato come amministratore per vedere questa pagina.</p>",
            403,
        )
    # Dati riservati, visibili SOLO all'admin autenticato.
    return f"""
    <!doctype html><html lang="it"><head><meta charset="utf-8">
    <title>Pannello amministratore</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 620px; margin: 50px auto;">
      <h1>Pannello amministratore</h1>
      <p>Benvenuto, <b>{session.get('username')}</b> (ruolo: amministratore).</p>
      <h2>Documenti riservati</h2>
      <ul>
        <li>Report finanziario Q4 (riservato)</li>
        <li>Elenco clienti premium (riservato)</li>
        <li><b>FLAG segreta: {FLAG}</b></li>
      </ul>
    </body></html>
    """


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=False)
