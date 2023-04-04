FROM archlinux:latest

WORKDIR /workspace

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm poppler python-aiogram typst

ADD typst.py bot.py ./

CMD ["/usr/bin/bash", "-c", "(python typst.py &); (python bot.py)"]
