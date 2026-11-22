FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      git tmux xvfb xauth procps ca-certificates curl jq \
      fonts-noto-cjk fonts-noto-color-emoji \
      libgtk-3-0 libnss3 libxss1 libasound2 libgbm1 libxshmfence1 libxkbfile1 libsecret-1-0 libdrm2 libatk-bridge2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m verifier && mkdir /work && chown verifier /work
USER verifier
WORKDIR /work
ENV LANG=ko_KR.UTF-8 ELECTRON_DISABLE_SANDBOX=1

COPY --chown=verifier . /work
RUN git config --global --add safe.directory /work && git config --global user.name verifier && git config --global user.email verifier@localhost
