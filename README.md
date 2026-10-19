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

## Validação de espessura

Medidas com espessura negativa ou maior que 10 mm são consideradas **nulas**:
isso indica que o produto provavelmente não está passando na máquina e a
produção está interrompida. O teste é feito sobre o valor final da medida —
após a última calibração, as subtrações e os filtros (média móvel) — e nunca
sobre distâncias brutas dos sensores. Valores nulos aparecem como lacunas no
gráfico e ficam fora das estatísticas (mínimo, média, máximo, % de
inconformidade etc.) no painel IHM e nas demais telas.

## Alarme sonoro (IHM)

Quando a espessura medida estiver fora dos limites de tolerância, o painel IHM
emite um alarme sonoro (bipes gerados pela Web Audio API). O alarme repete no
máximo uma vez por **cooldown**, enquanto a não conformidade persistir. O valor
do cooldown (padrão: 180 s = 3 min) é configurável em **Configurações e Debug**
(`/debug`).

> **Kiosk no Raspberry Pi:** navegadores bloqueiam áudio até o primeiro toque ou
> clique na página. Para o alarme soar sem interação, inicie o navegador com
> `--autoplay-policy=no-user-gesture-required` (ex.: no modo kiosk do Chromium).
