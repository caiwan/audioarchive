ARG base_image
FROM $base_image AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# TODO: Pin all version

RUN set -eux \
    && apt update >/dev/null 2>&1 \
    && apt install -y software-properties-common >/dev/null 2>&1 \
    && add-apt-repository ppa:deadsnakes/ppa >/dev/null 2>&1 \
    && apt update >/dev/null 2>&1 \
    && apt install -y \
        python3.8 \
        python3-pip \
        libsndfile1 \
        ffmpeg \
    && python3 -m pip install -U pip==22.3 pip-tools==6.8.0

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
    && python3 -m pip install autoflake8==0.4.0 black==22.10.0 \
    && ln -s /usr/bin/pip /usr/bin/pip3.8 \
    && pip-compile --output-file /tmp/requirements.txt /tmp/app/setup.cfg \
    && pip-compile --extra test --output-file /tmp/test-requirements.txt /tmp/app/setup.cfg \
	&& python3 -m pip install -r /tmp/requirements.txt \
    && python3 -m pip install -r /tmp/test-requirements.txt \
    && rm -rf /tmp/* 

# ---
# TODO: 
# FROM $base_image AS node-builder

# ---
FROM python-builder AS dev

RUN set -eux \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt update \
    && apt install -y yarn \
    && yarn global add @vue/cli

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
RUN rm -rf /tmp/* /var/cache/apk/*
CMD ["'/entrypoint.sh'"]

# TODO: Add frontend