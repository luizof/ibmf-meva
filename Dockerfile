# Usar a imagem oficial do Python como base
FROM python:3.9-slim

# Configurar diretório de trabalho no container
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação para o container
COPY MEVA/ /app/MEVA/
COPY scripts/ /app/scripts/

# Tornar os scripts executáveis
RUN chmod +x /app/scripts/*.sh

# Expor a porta 5000 (ou a porta em que seu Flask está rodando)
EXPOSE 4999

# Script de entrada que inicia o PostgreSQL e depois a aplicação
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
