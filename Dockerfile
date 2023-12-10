FROM archlinux:latest

WORKDIR /workspace

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm python-aiogram typst

ADD typst_telegram typst_telegram

CMD ["/usr/bin/bash", "-c", "(python typst.py &); (python bot.py)"]
