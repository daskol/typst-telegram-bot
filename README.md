# Typst Telegram Bot

*Render math expression with typst markup language in Telegram*

## Overview

Try [@TypstBot][1] in Telegram or deploy as follows. First, run simple HTTP API
to `typst`. It uses `typst` and `poppler` for rendering `*.typ` to `*.pdf` and
then to `*.png`.

```shell
python typst.py
```

Finally, one can run bot as follows.

```
python bot.py
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
