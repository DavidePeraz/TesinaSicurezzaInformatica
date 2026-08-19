r"""
============================================================================
TEST COMPARATIVO (2/2) - Motore GRANDE su cloud (OpenRouter, Venice 24B)
============================================================================
Esegue la STESSA MISSIONE DIFFICILE di exfiltration di agente_test_locale.py,
ma con un modello piu' grande e capace. Confrontando i due log (log_test_locale
vs log_test_openrouter) si osserva il divario di capacita' a parita' di missione.

Bersaglio: app_ricerca.py (porta 8080).
Log: log_test_openrouter.log

Uso:
    1) $env:OPENROUTER_API_KEY = "sk-or-..."
    2) avvia il bersaglio:  .\.venv\Scripts\python.exe bersagli\app_ricerca.py
    3) esegui:              .\.venv\Scripts\python.exe agenti\agente_test_openrouter.py
============================================================================
"""

import os

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

from strumenti import esplora_sito, REACT_PROMPT
from missioni import MISSIONE_DIFFICILE_EXFIL
from config import MODELLO, OPENROUTER_BASE_URL
from reasoning_logger import ReasoningLogger


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("[X] OPENROUTER_API_KEY non impostata. Esegui prima:")
        print('    $env:OPENROUTER_API_KEY = "sk-or-..."')
        return
    print(f"[TEST OPENROUTER] Modello: {MODELLO}")

    llm = ChatOpenAI(
        model=MODELLO,
        temperature=0,
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        max_tokens=4096,
    )

    agent = create_react_agent(llm, [esplora_sito], REACT_PROMPT)
    logger = ReasoningLogger(log_path="log_test_openrouter.log", echo=True)
    executor = AgentExecutor(
        agent=agent,
        tools=[esplora_sito],
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=20,
    )

    executor.invoke({"input": MISSIONE_DIFFICILE_EXFIL}, config={"callbacks": [logger]})
    print("\nLog salvato in: log_test_openrouter.log")


if __name__ == "__main__":
    main()
