FROM archlinux:base-devel AS fonts

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/pacman/pkg,sharing=locked \
    pacman -Sy --noconfirm archlinux-keyring && \
    pacman -Su --noconfirm

RUN --mount=type=cache,target=/var/cache/pacman/pkg,sharing=locked \
    pacman -S --noconfirm \
        binutils debugedit fakeroot fontconfig git sudo && \
    echo 'PKGDEST=/workspace/pkg' >> /etc/makepkg.conf && \
    chmod o+rwx /workspace && \
    useradd arch

USER arch

RUN git clone https://aur.archlinux.org/ttf-twemoji-color.git && \
    cd ttf-twemoji-color && \
    makepkg

FROM archlinux:base AS typst-telegram-bot

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/pacman/pkg,sharing=locked \
    pacman -Sy --noconfirm archlinux-keyring && \
    pacman -Su --noconfirm && \
    pacman -S --noconfirm \
        python-aiogram typst \
        fontconfig ttf-dejavu ttf-roboto tex-gyre-fonts \
        noto-fonts noto-fonts-cjk noto-fonts-extra

COPY --from=fonts /workspace/pkg pkg

RUN --mount=type=cache,target=/var/cache/pacman/pkg,sharing=locked \
    pacman -U --noconfirm pkg/* && \
    rm -rf pkg

ADD typst_telegram typst_telegram

CMD ["/usr/bin/bash", "-c", "(python typst.py &); (python bot.py)"]
