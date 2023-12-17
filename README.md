# Typst Telegram Bot

*Render math expression with typst markup language in Telegram*

## Overview

Try [@TypstBot][1] in Telegram or deploy as follows. First, run simple HTTP API
to `typst`. It uses `typst` for rendering `*.typ` to `*.png`.

```shell
typst-telegram serve api \
    --root-dir data \
    --endpoint http://localhost:8080 \
    --interface 127.0.0.1
```

Finally, one can run Telegram bot itself as follows with environemnt variable
`TELEGRAM_BOT_TOKEN` set.

```shell
typst-telegram serve bot --endpoint http://localhost:8080
```

[1]: https://t.me/TypstBot

## Deployment

Currently, deployment is based on Compose plugin but deployment requires some
preparation. We need to create directory `data` and properly assign ownership.

```shell
mkdir data
chown -R nobody:nobody data
```

Finally, one can run services as follows.

```shell
docker compose up -d
```
