ARG base_image
FROM $base_image AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# TODO: Pin all version

# Install required tools and add deadsnakes repository for Python 3.8
RUN apt update && \
    apt install -y software-properties-common && \
    apt install -y \
        gnupg2 \
        build-essential \
        zlib1g-dev \
        libncurses5-dev \
        libgdbm-dev \
        libnss3-dev \
        libssl-dev \
        libreadline-dev \
        libffi-dev \
        libsqlite3-dev \
        wget \
        libbz2-dev \
        python3.8 \
        python3-pip \
        libsndfile1 \
        ffmpeg 

# Set Python 3.8 as the default Python version
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1

ENTRYPOINT ["bash", "-c"]

# ---
FROM base AS python-builder
COPY ./ /tmp/app 
RUN set -eux \
    && apt install -y \
        build-essential \
		git \
        curl \
        python3.8-dev \
        python3.8-venv \
        libsndfile1-dev \
    && python3 -m pip install \
        autoflake8==0.4.0 \
        black==22.10.0 \
        pip-tools==7.3.0 \ 
    && ln -s /usr/bin/pip /usr/bin/pip3.8

RUN pip-compile --output-file /tmp/requirements.txt /tmp/app/setup.cfg \
    && pip-compile --extra test --output-file /tmp/test-requirements.txt /tmp/app/setup.cfg \
	&& python3 -m pip install -r /tmp/requirements.txt \
    && python3 -m pip install -r /tmp/test-requirements.txt \
    && rm -rf /tmp/* 

# ---
# TODO: 
# FROM $base_image AS node-builder

# ---
FROM python-builder AS dev

RUN apt update && \
    apt install -y \
        zsh \
        neovim

# RUN curl -o /tmp/btop.tbz https://github.com/aristocratos/btop/releases/latest/download/btop-x86_64-linux-musl.tbz \
#     && tar xf /tmp/btop.tbz --strip-components=2 -C /usr/local ./btop/bin/btop

RUN set -eux \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt update \
    && apt install -y yarn \
    && yarn global add @vue/cli

ENV CHSH='no'
ENV RUNZSH='no'
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
RUN chsh -s $(which zsh)

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

CMD ["sleep", "infinity"]

# ---- 


# TODO: copy artefacts form builder to app and frontend

FROM base as app
COPY ./ /app

# TODO: This should be copied to a tmp dir first then install as a module (eg. w/o -e)
WORKDIR /app
RUN python3 -m pip install --no-cache-dir --compile -e ./ 

COPY ./config.yaml /config/config.yaml
COPY ./logging.config /config/logging.config

COPY ./entrypoint.sh /entrypoint.sh

# Final cleanup 
# TODO: some parts of the bulidng evnironment is required after (gcc and such)
# RUN apk del .build-deps 
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

CMD ["'/entrypoint.sh'"]

# TODO: Add frontend