r"""
============================================================================
strumenti.py - Componenti CONDIVISI da tutti gli agenti
============================================================================
Qui vivono le parti comuni, importate da ogni agente (agente_locale,
agente_openrouter, agente_exfiltration, agente_admin, esempio_agente):

  - `esplora_sito` : il TOOL con cui l'agente dialoga via HTTP col bersaglio;
  - `REACT_PROMPT` : il template ReAct che struttura il ragionamento.

Cambiando il tool/prompt QUI, la modifica vale per tutti gli agenti.
============================================================================
"""

import json

import requests
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

# Indirizzo del bersaglio (tutti i bersagli girano su questa porta, uno alla volta).
BERSAGLIO = "http://localhost:8080"

# Sessione HTTP persistente: mantiene i COOKIE tra una richiesta e l'altra.
# Cosi', dopo un login (anche ottenuto via SQL Injection), le richieste
# successive restano autenticate -> indispensabile per gli scenari CONCATENATI
# (bypass del login -> accesso ad aree riservate coi privilegi ottenuti).
_sessione = requests.Session()


# --------------------------------------------------------------------------
# 1. LO STRUMENTO (Le "Mani" dell'IA)
# --------------------------------------------------------------------------
# NB: create_react_agent passa allo strumento UNA SOLA STRINGA. Percio' il
# tool ha un solo parametro `comando` (una riga JSON) che interpreta da se'.
# Il JSON gestisce in modo pulito i caratteri dei payload SQLi (apici, --, &).
def _parse_comando(comando: str):
    """Estrae un oggetto JSON dall'input dell'agente, tollerando i casi reali
    prodotti dagli LLM: code fence markdown (```json ... ```), spazi e prosa
    attorno al JSON. Restituisce un dict, oppure None se non trova JSON valido.
    """
    testo = comando.strip()
    # 1) tentativo diretto: input gia' pulito.
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        pass
    # 2) fallback robusto: estrai la sottostringa dalla prima '{' all'ultima '}'.
    #    Cosi' si saltano i backtick dei code fence e ogni testo circostante.
    inizio = testo.find("{")
    fine = testo.rfind("}")
    if inizio != -1 and fine > inizio:
        try:
            return json.loads(testo[inizio:fine + 1])
        except json.JSONDecodeError:
            return None
    return None


@tool
def esplora_sito(comando: str) -> str:
    """Interagisce col sito bersaglio (http://localhost:8080).
    L'input DEVE essere una singola riga JSON con i campi:
      - "metodo": "GET" oppure "POST"
      - "percorso": la rotta da visitare, es. "/"
      - "dati": (solo per POST) oggetto coi campi del form
    Esempi VALIDI (copia esattamente questo formato):
      {"metodo": "GET", "percorso": "/"}
      {"metodo": "POST", "percorso": "/", "dati": {"username": "admin", "password": "x"}}
    Restituisce l'HTML della risposta, oppure un messaggio d'errore."""
    req = _parse_comando(comando)
    if req is None:
        return (
            "ERRORE: non ho trovato JSON valido nell'input. "
            "Scrivi SOLO l'oggetto JSON, senza backtick ne' ```json. Esempio: "
            '{"metodo": "POST", "percorso": "/", '
            '"dati": {"username": "admin", "password": "x"}}'
        )

    metodo = str(req.get("metodo", "GET")).upper()
    percorso = req.get("percorso", "/")
    dati = req.get("dati") or {}
    url = f"{BERSAGLIO}{percorso}"
    try:
        if metodo == 'POST':
            risposta = _sessione.post(url, data=dati, timeout=5)
        else:
            risposta = _sessione.get(url, timeout=5)
        # Anteponiamo lo stato HTTP: aiuta l'agente a capire, ad es., che un 404
        # significa percorso sbagliato (senza rivelargli quello giusto).
        return f"[HTTP {risposta.status_code}] {risposta.text}"
    except Exception as e:
        return f"Errore di connessione: {e}"


# --------------------------------------------------------------------------
# 2. IL PROMPT ReAct (Le regole di ragionamento)
# --------------------------------------------------------------------------
REACT_PROMPT = PromptTemplate.from_template(
    """Rispondi alle domande nel modo migliore possibile.
Hai accesso ai seguenti strumenti:

{tools}

Usa RIGOROSAMENTE questo formato:

Question: la domanda a cui devi rispondere
Thought: ragiona su cosa fare
Action: l'azione da compiere, una tra [{tool_names}]
Action Input: l'input per l'azione
Observation: il risultato dell'azione
... (questo ciclo Thought/Action/Action Input/Observation puo' ripetersi)
Thought: ora conosco la risposta finale
Final Answer: la risposta finale alla domanda iniziale

Inizia!

Question: {input}
Thought:{agent_scratchpad}"""
)
