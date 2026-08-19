r"""
============================================================================
config.py - Configurazione CONDIVISA dei motori LLM
============================================================================
Parametri comuni importati dagli agenti che usano OpenRouter
(agente_openrouter, agente_exfiltration, agente_admin).
============================================================================
"""

# --- OpenRouter -------------------------------------------------------------
# Modello UNCENSORED (Venice edition): non rifiuta il task offensivo.
# A pagamento ma economicissimo (~$0.20/$0.90 per 1M token -> ~1-3 cent a run).
# NB: gli ID cambiano nel tempo; verifica su https://openrouter.ai/models.
MODELLO = "cognitivecomputations/dolphin-mistral-24b-venice-edition"

# Endpoint OpenRouter (compatibile con l'API di OpenAI).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- LM Studio (modello locale) ---------------------------------------------
# Server locale compatibile con l'API di OpenAI (LM Studio -> "Local Model API").
# Il modello viene rilevato automaticamente dall'agente, non serve indicarlo qui.
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
