# Usar a imagem oficial do Python como base
FROM python:3.9-slim

# Configurar diretório de trabalho no container
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de requisitos e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação para o container
COPY MEVA/ /app/MEVA/
COPY scripts/ /app/scripts/
COPY scripts/wait-for-it.sh /usr/local/bin/wait-for-it.sh

# Tornar os scripts executáveis
RUN chmod +x /usr/local/bin/wait-for-it.sh /app/scripts/*.sh

# Expor a porta 5000 (ou a porta em que seu Flask está rodando)
EXPOSE 4999

# Comando para iniciar o servidor Python usando wait-for-it para garantir que o DB está pronto
CMD ["wait-for-it.sh", "db:5432", "--", "python", "/app/MEVA/MEVA.py"]
