ARG base_image
FROM $base_image AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN set -eux \
    && apt update >/dev/null 2>&1 \
    && apt install -y software-properties-common >/dev/null 2>&1 \
    && add-apt-repository ppa:deadsnakes/ppa >/dev/null 2>&1 \
    && apt update >/dev/null 2>&1 \
    && apt install -y gcc python3-dev python3-venv python3-pip libsndfile-dev \
    && python3 -m pip install -U pip==22.2.2 pip-tools==6.8.0

# ---
FROM base AS dev

ENTRYPOINT ["bash", "-c"]

# ---- 

# TODO: Add builder image 
# TODO: copy artefacts form builder to app 

FROM dev as app

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