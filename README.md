# meva
Medidor de Espessura de Vinílicos Arquitech

## Executar com Docker

Toda a aplicação e o banco de dados rodam agora em um único container.

Para construir a imagem:

```
docker build -t meva .
```

E para executar:

```
docker run -p 4999:4999 meva
```

O container inicia o PostgreSQL, cria o banco `BD_MEP` com as tabelas definidas em
`scripts/create_tables.sql` e em seguida executa a aplicação Flask.
