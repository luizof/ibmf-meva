# meva
Medidor de Espessura de Vinílicos Arquitech

## Executar com Docker

Toda a aplicação e o banco de dados rodam agora em um único container.

Para construir a imagem:

```
docker build -t meva .
```

A imagem instala o PostgreSQL disponível na distribuição.
O diretório de dados utilizado pela imagem única é `/var/lib/postgresql/data`.
No `docker-compose.yml` usa-se a imagem oficial do Postgres, cujo volume padrão
também é `/var/lib/postgresql/data`.

E para executar:

```
docker run -p 80:80 meva
```

Se desejar persistir os dados localmente, mapeie um volume para o diretório de
dados do container:

```
docker run -p 80:80 \
  -v $(pwd)/pgdata:/var/lib/postgresql/data \
  meva
```

O entrypoint do container inicializa esse diretório automaticamente caso ele
esteja vazio.

O container inicia o PostgreSQL, cria o banco `BD_MEP` com as tabelas definidas em
`scripts/create_tables.sql` e em seguida executa a aplicação Flask.
Para evitar problemas de codificacao, o `docker-compose.yml` define a variavel `POSTGRES_INITDB_ARGS` com `--encoding=UTF8`. Assim o cluster do PostgreSQL e inicializado em UTF-8 e aceita corretamente dados com acentuacao.
