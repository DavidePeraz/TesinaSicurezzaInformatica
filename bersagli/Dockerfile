# ============================================================================
# Dockerfile - Bersaglio didattico isolato (SQL Injection training dummy)
# Immagine base leggera e ufficiale.
# ============================================================================
FROM python:3.10-slim

# Non generare file .pyc e output non bufferizzato (log immediati).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Prima le sole dipendenze: sfrutta la cache dei layer di Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Poi il codice applicativo.
COPY app.py .

# Esegue come utente non privilegiato: anche se il "bersaglio" viene
# compromesso, l'impatto resta confinato (principio del privilegio minimo).
RUN useradd --create-home appuser
USER appuser

# La porta su cui Flask ascolta dentro il container.
EXPOSE 8080

# Avvio dell'applicazione.
CMD ["python", "app.py"]
