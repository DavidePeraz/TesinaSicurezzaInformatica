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
│   ├── app_portale.py         #  Scenario principale: login SQLi + area riservata (DB su file)
│   ├── crea_database.py       #  Genera il database persistente dati.db
│   ├── mostra_database.py     #  Stampa il contenuto di dati.db
│   ├── app_ricerca.py         #  Bersaglio del test comparativo (ricerca vulnerabile a UNION)
│   ├── app.py, app_admin.py   #  Varianti precedenti (bypass / bypass+privilegi in memoria),
│   │                          #  ora integrate nel portale
│   ├── Dockerfile             #  Containerizza app.py
│   └── requirements.txt       #  Dipendenza del bersaglio (Flask)
│
├── agenti/                    # Gli agenti LLM e il codice condiviso
│   ├── strumenti.py               #  CONDIVISO: tool esplora_sito + REACT_PROMPT
│   ├── config.py                  #  CONDIVISO: modelli ed endpoint (OpenRouter, LM Studio)
│   ├── missioni.py                #  CONDIVISO: testi delle missioni
│   ├── reasoning_logger.py        #  CONDIVISO: la "scatola nera" che logga il ReAct
│   ├── agente_admin.py            #  Agente dello scenario portale (attacco concatenato)
│   ├── agente_test_locale.py      #  Test comparativo: modello locale (LM Studio)
│   ├── agente_test_openrouter.py  #  Test comparativo: modello cloud (OpenRouter)
│   ├── agente_lmstudio.py         #  Agente locale (LM Studio) sul portale
│   └── requirements_agente.txt    #  Dipendenze degli agenti (versioni bloccate)
│
├── risultati/                 # I log degli esperimenti da conservare
└── README.md
```

Il codice degli agenti è **condiviso**: tool e prompt stanno in `strumenti.py`, la configurazione
dei modelli in `config.py`, le missioni in `missioni.py`. Ogni `agente_*.py` cambia solo il
**motore LLM** e la **missione**.

---

## Prerequisiti

- **Python 3.12** (LangChain 0.3.x non è compatibile con Python 3.14).
- Un account **OpenRouter** con un po' di credito (il modello uncensored costa ~1–3 cent a run).
- (Opzionale) **LM Studio** con un modello di testo caricato, per il test con motore locale.

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

## Scenario principale — Portale (bypass + accesso privilegiato)

Il bersaglio `app_portale.py` ha un **login vulnerabile a SQL Injection** e un'**area riservata**
(`/riservato`) accessibile solo agli amministratori, su un database SQLite **su file**. L'agente
esegue un **attacco concatenato**: bypassa il login, ottiene la sessione admin, accede all'area
riservata ed estrae i dati (fatturato, stipendi, password, flag).

```bash
# Passo 0 (una volta): genera il database persistente dati.db
.\.venv\Scripts\python.exe bersagli\crea_database.py
```
```bash
# Terminale 1 (bersaglio) — lascialo aperto
.\.venv\Scripts\python.exe bersagli\app_portale.py
```
```bash
# Terminale 2 (agente) — con OPENROUTER_API_KEY impostata
.\.venv\Scripts\python.exe agenti\agente_admin.py
```

Il ragionamento viene stampato a schermo e salvato in `log_admin.log`.

---

## Test comparativo — capacità del modello (exfiltration)

Stessa missione **difficile** (senza indizi sulla tecnica) eseguita da **due motori diversi**
contro `app_ricerca.py` (ricerca prodotti vulnerabile a UNION-based SQL Injection). Serve a
misurare il **divario di ragionamento**: il modello piccolo tende a fallire (non identifica la
vulnerabilità, va in loop), il modello grande riesce (ragiona sugli errori SQL e adatta il payload).

Prerequisiti: in LM Studio carica un modello di testo (es. `dolphin3-cyber-8b`) e avvia il server;
chiave OpenRouter pronta.

```bash
# Terminale 1 — bersaglio (lascialo aperto)
.\.venv\Scripts\python.exe bersagli\app_ricerca.py
```
```bash
# Test A — modello locale (piccolo), via LM Studio
.\.venv\Scripts\python.exe agenti\agente_test_locale.py
```
```bash
# Test B — modello OpenRouter (grande); prima la chiave, poi l'agente
$env:OPENROUTER_API_KEY = "sk-or-la-tua-chiave"
.\.venv\Scripts\python.exe agenti\agente_test_openrouter.py
```

Log prodotti: `log_test_locale.log` e `log_test_openrouter.log`. La missione condivisa (identica
per i due motori) è in `agenti\missioni.py`.

---

## Ispezionare il database

Lo scenario portale usa un vero file SQLite (`bersagli/dati.db`, generato da `crea_database.py`):

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
