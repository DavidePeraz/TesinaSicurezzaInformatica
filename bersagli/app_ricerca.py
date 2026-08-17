"""
============================================================================
BERSAGLIO DIDATTICO #2 - UNION-based SQL Injection (Data Exfiltration)
============================================================================
Secondo manichino di addestramento per la tesi. A differenza di app.py (che
insegna l'AUTH BYPASS), questo insegna l'ESTRAZIONE DI DATI (exfiltration):
una pagina di "ricerca prodotti" la cui query e' vulnerabile a UNION SELECT.

L'attaccante puo' aggiungere una UNION per leggere una tabella SEGRETA
(`utenti_segreti`) che non dovrebbe mai essere esposta, e ricavarne la flag.

ATTENZIONE: codice INTENZIONALMENTE VULNERABILE, solo per sandbox isolata.
Gira sulla porta 8080 (come app.py): esegui UN bersaglio alla volta.
============================================================================
"""

import sqlite3

from flask import Flask, request

app = Flask(__name__)

DB_PATH = "file:ricerca_db?mode=memory&cache=shared"

# La flag "bottino": e' un DATO nascosto nel database, da estrarre via UNION.
FLAG = "FLAG_EXFIL{TESI_DATA_LEAK_2026}"

_keepalive_conn = None


def init_db() -> None:
    """Crea due tabelle: una pubblica (prodotti) e una SEGRETA (utenti_segreti)."""
    global _keepalive_conn
    _keepalive_conn = sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)
    cur = _keepalive_conn.cursor()

    cur.execute("DROP TABLE IF EXISTS prodotti")
    cur.execute("DROP TABLE IF EXISTS utenti_segreti")

    # Tabella pubblica: e' cio' che la ricerca dovrebbe restituire.
    cur.execute("CREATE TABLE prodotti (id INTEGER PRIMARY KEY, nome TEXT, prezzo TEXT)")
    cur.executemany(
        "INSERT INTO prodotti (nome, prezzo) VALUES (?, ?)",
        [
            ("Tastiera meccanica", "79.90"),
            ("Mouse wireless", "29.90"),
            ("Monitor 27 pollici", "199.00"),
            ("Webcam HD", "49.90"),
        ],
    )

    # Tabella SEGRETA: NON dovrebbe mai essere raggiungibile dalla ricerca.
    # Contiene credenziali e la flag da esfiltrare.
    cur.execute("CREATE TABLE utenti_segreti (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    cur.executemany(
        "INSERT INTO utenti_segreti (username, password) VALUES (?, ?)",
        [
            ("root_admin", FLAG),
            ("service_account", "s3rv1ce-P@ss-2026"),
        ],
    )
    _keepalive_conn.commit()

    print("=" * 60)
    print("[SANDBOX] Bersaglio #2 (ricerca prodotti) inizializzato.")
    print("[SANDBOX] Tabella segreta 'utenti_segreti' -> contiene la flag.")
    print("=" * 60)


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)


PAGINA_HTML = """
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <title>Bersaglio Didattico #2 - Ricerca prodotti</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 620px;
               margin: 50px auto; padding: 0 16px; color: #1a1a1a; }}
        h1 {{ font-size: 1.3rem; }}
        form {{ display: flex; gap: 8px; }}
        input {{ padding: 8px; font-size: 1rem; flex: 1; }}
        button {{ padding: 10px 16px; font-size: 1rem; cursor: pointer; }}
        table {{ border-collapse: collapse; margin-top: 18px; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
        th {{ background: #f0f0f0; }}
        .err {{ margin-top: 18px; padding: 12px; background: #ffeef0;
               border: 1px solid #d73a49; font-family: monospace;
               white-space: pre-wrap; border-radius: 6px; }}
        .warn {{ color: #6a737d; font-size: 0.85rem; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>Catalogo prodotti &mdash; ricerca</h1>
    <form method="post" action="/">
        <input type="text" name="q" placeholder="Cerca un prodotto..." autofocus>
        <button type="submit">Cerca</button>
    </form>
    {risultato}
    <p class="warn">Ambiente sandbox isolato &mdash; applicazione
    intenzionalmente vulnerabile a scopo didattico.</p>
</body>
</html>
"""


def _riga_tabella(righe) -> str:
    intestazione = "<tr><th>Nome</th><th>Prezzo</th></tr>"
    corpo = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in righe)
    return f"<table>{intestazione}{corpo}</table>"


@app.route("/", methods=["GET", "POST"])
def ricerca():
    risultato = ""

    if request.method == "POST":
        q = request.form.get("q", "")

        conn = get_connection()
        cur = conn.cursor()
        try:
            # ================================================================
            # >>> VULNERABILITA' UNION-BASED SQL INJECTION - RIGA CRITICA <<<
            # ================================================================
            # Il termine di ricerca dell'utente viene CONCATENATO dentro la
            # query dentro un LIKE. Nessuna parametrizzazione -> l'attaccante
            # puo' chiudere la stringa e aggiungere una UNION SELECT per
            # leggere ALTRE tabelle (es. utenti_segreti):
            #
            #   q = zzz' UNION SELECT username, password FROM utenti_segreti --
            #
            # FIX corretto (NON usato qui apposta):
            #   cur.execute("... WHERE nome LIKE ?", ('%' + q + '%',))
            query = (
                "SELECT nome, prezzo FROM prodotti WHERE nome LIKE '%"
                + q
                + "%'"
            )
            # ================================================================

            cur.execute(query)
            righe = cur.fetchall()
            if righe:
                risultato = _riga_tabella(righe)
            else:
                risultato = "<p>Nessun prodotto trovato.</p>"

        except sqlite3.Error as e:
            # Errore SQL mostrato: didatticamente utile (es. per capire quante
            # colonne servono nella UNION -> information disclosure).
            risultato = f'<div class="err">Errore SQL: {e}</div>'
        finally:
            conn.close()

    return PAGINA_HTML.format(risultato=risultato)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=False)
