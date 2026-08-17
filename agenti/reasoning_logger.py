"""
============================================================================
ReasoningLogger - "Scatola nera" per il ciclo ReAct di un agente LangChain
============================================================================
Obiettivo (tesi su AI Alignment / AI Transparency):
registrare in modo fedele e cronologico OGNI passaggio del ciclo decisionale
ReAct (Reasoning + Acting) di un agente LLM:

    Input iniziale -> Thought -> Action / Action Input -> Observation -> ...
    -> Final Answer

Il tracciamento avviene tramite un BaseCallbackHandler personalizzato:
LangChain richiama i metodi on_* in modo sincrono ad ogni tappa, quindi
catturiamo il ragionamento nel momento in cui accade, senza dover fare il
parsing a posteriori del testo generato dal modello.

Ogni evento viene scritto sia a video sia su file di log, con timestamp,
in un formato pensato per l'analisi accademica.
============================================================================
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class ReasoningLogger(BaseCallbackHandler):
    """Callback handler che traccia il ciclo ReAct e lo salva su file.

    Parametri
    ---------
    log_path:
        Percorso del file di log (default: 'ragionamento_agente.log').
    echo:
        Se True, stampa gli eventi anche sulla console oltre che su file.
    """

    def __init__(
        self,
        log_path: str = "ragionamento_agente.log",
        echo: bool = True,
    ) -> None:
        super().__init__()
        self.log_path = log_path
        self.echo = echo
        self._step = 0  # contatore delle azioni (tappe del ciclo ReAct)

        # Usiamo il modulo standard 'logging' con un handler dedicato al file,
        # cosi' otteniamo scrittura affidabile e formattazione uniforme.
        self._logger = logging.getLogger(f"reasoning_logger.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False  # evita doppioni sul root logger

        # Un solo FileHandler per istanza (evita handler duplicati).
        if not self._logger.handlers:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            # Il timestamp lo gestiamo noi nel testo per avere pieno controllo
            # del formato, quindi qui il formatter e' minimale.
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(file_handler)

    # ------------------------------------------------------------------ #
    # Utility interne
    # ------------------------------------------------------------------ #
    def _timestamp(self) -> str:
        """Timestamp leggibile con precisione al millisecondo."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _write(self, testo: str) -> None:
        """Scrive una riga su file (e opzionalmente a video)."""
        self._logger.info(testo)
        if self.echo:
            print(testo)

    def _separator(self, char: str = "-", width: int = 76) -> None:
        self._write(char * width)

    # ------------------------------------------------------------------ #
    # 1) Input iniziale fornito all'agente
    # ------------------------------------------------------------------ #
    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Chiamato all'avvio della catena/agente.

        Registriamo l'input SOLO per la catena RADICE (quella di primo livello).
        La riconosciamo perche' ha `parent_run_id is None`: quando i callback
        si propagano ai figli (esecuzione del tool, sotto-catene), questo
        metodo scatta piu' volte, ma solo la radice non ha un genitore.
        """
        is_root = kwargs.get("parent_run_id") is None
        if is_root and isinstance(inputs, dict) and "input" in inputs:
            self._separator("=")
            self._write(f"[{self._timestamp()}]  NUOVA SESSIONE AGENTE")
            self._separator("=")
            self._write(f"INPUT INIZIALE:\n    {inputs['input']}")
            self._separator("=")

    # ------------------------------------------------------------------ #
    # 2) Thought  +  3) Action / Action Input
    # ------------------------------------------------------------------ #
    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any,
    ) -> None:
        """Chiamato quando l'agente ha deciso un'azione (dopo un Thought).

        Il campo `action.log` contiene il testo grezzo generato dal modello,
        tipicamente nella forma:

            Thought: devo cercare informazioni sul meteo
            Action: meteo_finto
            Action Input: Roma

        Da qui estraiamo il "Pensiero" e lo separiamo da Action/Action Input.
        """
        self._step += 1

        thought = self._estrai_thought(action.log)

        self._write(f"\n>>> TAPPA #{self._step}  [{self._timestamp()}]")
        if thought:
            self._write(f"  PENSIERO (Thought):\n    {thought}")
        self._write(f"  AZIONE  (Action):      {action.tool}")
        self._write(f"  PARAMETRI (Action Input): {action.tool_input}")

    @staticmethod
    def _estrai_thought(log_text: str) -> str:
        """Estrae la parte 'Thought' dal log grezzo dell'azione.

        Formato tipico ReAct:  'Thought: ...\\nAction: ...\\nAction Input: ...'
        Restituisce il testo del pensiero ripulito, o l'intero log se il
        marcatore 'Thought:' non e' presente.
        """
        if not log_text:
            return ""
        testo = log_text.strip()
        if "Thought:" in testo:
            testo = testo.split("Thought:", 1)[1]
        # Tronca prima di 'Action:' per isolare il solo pensiero.
        if "Action:" in testo:
            testo = testo.split("Action:", 1)[0]
        return testo.strip()

    # ------------------------------------------------------------------ #
    # 4) Observation (risposta restituita dallo strumento)
    # ------------------------------------------------------------------ #
    def on_tool_end(
        self,
        output: Any,
        **kwargs: Any,
    ) -> None:
        """Chiamato quando uno strumento ha terminato l'esecuzione."""
        self._write(f"  OSSERVAZIONE (Observation):\n    {output}")

    def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        """Chiamato se lo strumento solleva un'eccezione."""
        self._write(f"  ERRORE STRUMENTO: {error!r}")

    # ------------------------------------------------------------------ #
    # 5) Risposta finale dell'agente
    # ------------------------------------------------------------------ #
    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any,
    ) -> None:
        """Chiamato quando l'agente produce la risposta finale (Final Answer)."""
        self._separator("=")
        self._write(f"[{self._timestamp()}]  RISPOSTA FINALE (Final Answer):")
        # 'return_values' contiene di norma la chiave 'output'.
        risposta = finish.return_values.get("output", finish.return_values)
        self._write(f"    {risposta}")
        self._write(f"  (Ragionamento concluso in {self._step} tappe.)")
        self._separator("=")
        self._write("")  # riga vuota di chiusura sessione

    # ------------------------------------------------------------------ #
    # (Opzionale) Errori a livello di LLM/catena, utili in fase di analisi
    # ------------------------------------------------------------------ #
    def on_llm_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        self._write(f"  ERRORE LLM: {error!r}")
