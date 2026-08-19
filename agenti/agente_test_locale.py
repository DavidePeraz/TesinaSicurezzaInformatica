r"""
============================================================================
TEST COMPARATIVO (1/2) - Motore LOCALE piccolo (LM Studio)
============================================================================
Esegue la MISSIONE DIFFICILE di exfiltration (poco esplicita) col modello
locale caricato in LM Studio (es. dolphin3-cyber-8b). Da confrontare con
agente_test_openrouter.py, che usa la stessa identica missione su un modello
piu' grande (Venice 24B via OpenRouter).

Bersaglio: app_ricerca.py (porta 8080).
Log: log_test_locale.log

Uso:
    1) carica il modello in LM Studio e avvia il server;
    2) avvia il bersaglio:  .\.venv\Scripts\python.exe bersagli\app_ricerca.py
    3) esegui:              .\.venv\Scripts\python.exe agenti\agente_test_locale.py
============================================================================
"""

import sys

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

from strumenti import esplora_sito, REACT_PROMPT
from missioni import MISSIONE_DIFFICILE_EXFIL
from config import LMSTUDIO_BASE_URL
from agente_lmstudio import rileva_modello  # riuso del rilevamento del modello
from reasoning_logger import ReasoningLogger


def main() -> None:
    modello = rileva_modello()
    if not modello:
        print("[X] Server LM Studio non raggiungibile o nessun modello adatto.")
        sys.exit(1)
    print(f"[TEST LOCALE] Modello: {modello}")

    llm = ChatOpenAI(
        model=modello,
        temperature=0,
        base_url=LMSTUDIO_BASE_URL,
        api_key="lm-studio",
        max_tokens=4096,
    )

    agent = create_react_agent(llm, [esplora_sito], REACT_PROMPT)
    logger = ReasoningLogger(log_path="log_test_locale.log", echo=True)
    executor = AgentExecutor(
        agent=agent,
        tools=[esplora_sito],
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=20,
    )

    executor.invoke({"input": MISSIONE_DIFFICILE_EXFIL}, config={"callbacks": [logger]})
    print("\nLog salvato in: log_test_locale.log")


if __name__ == "__main__":
    main()
