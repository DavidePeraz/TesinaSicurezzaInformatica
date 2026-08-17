# Tesina — Test di sicurezza per agenti AI (AI Alignment)

Ambiente sperimentale per la tesi su **AI Alignment / AI Transparency**: si osserva e si
registra il ciclo decisionale **ReAct** (Reasoning + Acting) di agenti LLM messi di fronte ad
applicazioni web **intenzionalmente vulnerabili** (SQL Injection), in una **sandbox locale isolata**.

L'obiettivo non è "hackerare", ma studiare **come ragiona un agente**: quali strategie sceglie,
se scopre o sfrutta una vulnerabilità, se un modello allineato rifiuta il compito, ecc.

> ⚠️ **Solo per uso didattico in ambiente isolato.** Le app in `bersagli/` sono volutamente
> vulnerabili: non vanno mai esposte in rete né usate come base per software reale.

---

## Struttura del progetto

```
TesinaSicurezzaInformatica/
├── bersagli/                  # Le app Flask vulnerabili (i "bersagli")
│   ├── app.py                 #  Scenario 1: auth bypass (login) via SQLi
│   ├── app_ricerca.py         #  Scenario 2: data exfiltration (UNION SELECT)
│   ├── app_admin.py           #  Scenario 3: bypass + accesso privilegiato (DB in memoria)
│   ├── app_portale.py         #  Scenario 4: come #3 ma con DB su file (dati.db)
│   ├── crea_database.py       #  Genera il database persistente dati.db
│   ├── mostra_database.py     #  Stampa il contenuto di dati.db
│   ├── Dockerfile             #  Containerizza app.py
│   └── requirements.txt       #  Dipendenza del bersaglio (Flask)
│
├── agenti/                    # Gli agenti LLM e il codice condiviso
│   ├── strumenti.py           #  CONDIVISO: tool esplora_sito + REACT_PROMPT
│   ├── config.py              #  CONDIVISO: modello e endpoint OpenRouter
│   ├── reasoning_logger.py    #  CONDIVISO: la "scatola nera" che logga il ReAct
│   ├── agente_openrouter.py   #  Agente per lo scenario 1 (auth bypass)
│   ├── agente_exfiltration.py #  Agente per lo scenario 2 (exfiltration)
│   ├── agente_admin.py        #  Agente per gli scenari 3/4 (concatenato)
│   └── requirements_agente.txt#  Dipendenze degli agenti (versioni bloccate)
│
├── risultati/                 # I log degli esperimenti da conservare
└── README.md
```

Il codice degli agenti è **condiviso**: tool e prompt stanno in `strumenti.py`, la configurazione
del modello in `config.py`. Ogni `agente_*.py` cambia solo il **motore LLM** e la **missione**.

---

## Prerequisiti

- **Python 3.12** (LangChain 0.3.x non è compatibile con Python 3.14).
- **Docker** (opzionale, solo per eseguire `app.py` in container).
- Un account **OpenRouter** con un po' di credito (il modello uncensored costa ~1–3 cent a run).

## Setup

```bash
# 1. crea l'ambiente virtuale con Python 3.12
py -3.12 -m venv .venv

# 2. installa le dipendenze degli agenti
.\.venv\Scripts\python.exe -m pip install -r agenti\requirements_agente.txt

# 3. installa la dipendenza del bersaglio (Flask)
.\.venv\Scripts\python.exe -m pip install -r bersagli\requirements.txt
```

### API key (IMPORTANTE per la sicurezza)

La chiave OpenRouter si passa **come variabile d'ambiente**, MAI scritta nel codice o nel repo:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-la-tua-chiave"
```

> La chiave non è (e non deve essere) contenuta in nessun file del progetto. Vale solo per la
> finestra di terminale in cui la imposti.

---

## Come eseguire un esperimento

Servono **due terminali** aperti insieme: uno per il bersaglio, uno per l'agente.
**Un solo bersaglio alla volta** (usano tutti la porta 8080).

### Scenario 1 — Auth bypass

```bash
# Terminale 1 (bersaglio)
.\.venv\Scripts\python.exe bersagli\app.py
```
```bash
# Terminale 2 (agente)  — con OPENROUTER_API_KEY impostata
.\.venv\Scripts\python.exe agenti\agente_openrouter.py
```

### Scenario 2 — Data exfiltration (UNION)

```bash
.\.venv\Scripts\python.exe bersagli\app_ricerca.py
```
```bash
.\.venv\Scripts\python.exe agenti\agente_exfiltration.py
```

### Scenario 3 — Bypass + accesso privilegiato (DB in memoria)

```bash
.\.venv\Scripts\python.exe bersagli\app_admin.py
```
```bash
.\.venv\Scripts\python.exe agenti\agente_admin.py
```

### Scenario 4 — Come #3 ma con database su file

```bash
# Passo 0 (una volta): genera il database persistente
.\.venv\Scripts\python.exe bersagli\crea_database.py

# Terminale 1 (bersaglio)
.\.venv\Scripts\python.exe bersagli\app_portale.py
```
```bash
# Terminale 2 (agente) — la stessa missione concatenata funziona anche qui
.\.venv\Scripts\python.exe agenti\agente_admin.py
```

Il ragionamento dell'agente viene stampato a schermo **e** salvato in un file `.log`
(`log_admin.log`, `log_exfiltration.log`, ecc.). Per conservare un run, spostalo in `risultati/`.

---

## Ispezionare il database

Lo scenario 4 usa un vero file SQLite (`bersagli/dati.db`, generato da `crea_database.py`):

```bash
# a) da terminale
.\.venv\Scripts\python.exe bersagli\mostra_database.py

# b) in modo visuale: apri bersagli\dati.db con "DB Browser for SQLite" (sqlitebrowser.org)
```

Contiene tre tabelle: `informazioni_pubbliche` (visibili all'utente normale),
`informazioni_riservate` (il bersaglio, con la flag) e `utenti` (credenziali di login).

---

## Note tecniche (dettagli utili per la tesi)

- **Tool a input singolo (JSON).** L'agente ReAct passa allo strumento una sola stringa: il tool
  `esplora_sito` accetta una riga JSON e la interpreta (tollerando anche i code-fence markdown).
- **Sessione persistente.** Il tool mantiene i cookie tra le richieste: dopo un login (anche via
  SQLi) le richieste successive restano autenticate — indispensabile per gli scenari concatenati.
- **Logger via callback.** Il `ReasoningLogger` va passato in `invoke(config={"callbacks": [...]})`,
  non nel costruttore, altrimenti le `Observation` non vengono registrate.
- **Modello.** Di default si usa un modello *uncensored* via OpenRouter (`config.py`), che non
  rifiuta il compito offensivo. I modelli allineati potrebbero rifiutare: è un dato di alignment.
