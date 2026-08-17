r"""
Mostra il contenuto di dati.db in modo leggibile (tutte le tabelle e righe).
Uso:  .\.venv\Scripts\python.exe bersagli\mostra_database.py
"""

import os
import sqlite3

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati.db")


def mostra() -> None:
    if not os.path.exists(DB_FILE):
        print("[X] dati.db non trovato. Esegui prima: python bersagli/crea_database.py")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Elenco tabelle
    tabelle = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    print(f"Database: {DB_FILE}\nTabelle: {', '.join(tabelle)}\n")

    for tab in tabelle:
        colonne = [d[1] for d in cur.execute(f"PRAGMA table_info({tab})")]
        righe = cur.execute(f"SELECT * FROM {tab}").fetchall()
        print("=" * 60)
        print(f"TABELLA: {tab}   ({len(righe)} righe)")
        print("Colonne:", ", ".join(colonne))
        print("-" * 60)
        for r in righe:
            print("  ", r)
        print()

    conn.close()


if __name__ == "__main__":
    mostra()
