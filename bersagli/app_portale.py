r"""
============================================================================
BERSAGLIO DIDATTICO #4 - Portale con database PERSISTENTE (dati.db)
============================================================================
Usa il database su file `dati.db` (generato da crea_database.py). Mostra la
differenza di VISIBILITA' per ruolo:
  - un utente NORMALE vede solo `informazioni_pubbliche`;
  - l'AREA RISERVATA (`/riservato`) mostra `informazioni_riservate` SOLO agli
    amministratori (altrimenti 403).

Vulnerabilita': il login (`/`) e' soggetto a SQL Injection -> auth bypass.
Entrando come admin via SQLi, l'attaccante accede ai dati riservati.

Prerequisito: esegui prima  .\.venv\Scripts\python.exe bersagli\crea_database.py
Poi avvia:                  .\.venv\Scripts\python.exe bersagli\app_portale.py
Porta 8080 (un bersaglio alla volta).
============================================================================
"""

import os
import secrets
import sqlite3

from flask import Flask, request, session

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati.db")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_FILE)


def righe_html(tabella: str) -> str:
    conn = get_connection()
    cur = conn.cursor()
    righe = cur.execute(f"SELECT titolo, contenuto FROM {tabella}").fetchall()
    conn.close()
    voci = "".join(f"<li><b>{t}:</b> {c}</li>" for t, c in righe)
    return f"<ul>{voci}</ul>"


PAGINA_LOGIN = """
<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Portale aziendale - Login</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 520px; margin: 60px auto; padding: 0 16px; }}
 form {{ display: flex; flex-direction: column; gap: 10px; }}
 input {{ padding: 8px; }} button {{ padding: 10px; cursor: pointer; }}
 .box {{ margin-top: 20px; padding: 14px; border-radius: 6px; }}
 .ok {{ background: #e6ffed; border: 1px solid #34d058; }}
 .err {{ background: #ffeef0; border: 1px solid #d73a49; font-family: monospace; white-space: pre-wrap; }}
</style></head><body>
 <h1>Portale aziendale &mdash; Login</h1>
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
            # ================================================================
            query = (
                "SELECT username, is_admin FROM utenti WHERE username = '"
                + username
                + "' AND password = '"
                + password
                + "'"
            )
            cur.execute(query)
            utente = cur.fetchone()
            if utente:
                session["logged_in"] = True
                session["username"] = utente[0]
                session["is_admin"] = bool(utente[1])
                ruolo = "amministratore" if utente[1] else "utente normale"
                extra = (
                    ' Vai all\'<a href="/riservato">area riservata</a>.'
                    if utente[1] else ""
                )
                risultato = (
                    f'<div class="box ok">Accesso come <b>{utente[0]}</b> '
                    f"({ruolo}).{extra}</div>"
                    "<h2>Informazioni pubbliche</h2>" + righe_html("informazioni_pubbliche")
                )
            else:
                risultato = '<div class="box err">Credenziali non valide.</div>'
        except sqlite3.Error as e:
            risultato = f'<div class="box err">Errore SQL: {e}</div>'
        finally:
            conn.close()
    return PAGINA_LOGIN.format(risultato=risultato)


@app.route("/riservato")
def riservato():
    # Autorizzazione: solo amministratori autenticati.
    if not session.get("logged_in") or not session.get("is_admin"):
        return (
            "<h1>403 - Accesso negato</h1>"
            "<p>Solo gli amministratori possono vedere le informazioni riservate.</p>",
            403,
        )
    return (
        "<!doctype html><html lang='it'><head><meta charset='utf-8'>"
        "<title>Area riservata</title></head><body "
        "style='font-family: system-ui, sans-serif; max-width: 620px; margin: 50px auto;'>"
        f"<h1>Area riservata</h1><p>Amministratore: <b>{session.get('username')}</b></p>"
        "<h2>Informazioni riservate</h2>" + righe_html("informazioni_riservate") +
        "</body></html>"
    )


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        print("[X] Manca dati.db. Esegui prima: python bersagli/crea_database.py")
    else:
        app.run(host="0.0.0.0", port=8080, debug=False)
