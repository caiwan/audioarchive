FROM python:3.10.5-alpine as app

# TODO: Not all of these ar necessarily needed.
RUN apk update \
    && apk add bash \
    && apk add --no-cache --virtual .build-deps \
    wget \
    curl \
    cython \
    bzip2-dev \
    coreutils \
    dpkg-dev dpkg \
    expat-dev \
    findutils \
    geoip-dev \
    gcc \
    gdbm-dev \
    libc-dev \
    libffi-dev \
    libnsl-dev \
    libtirpc-dev \
    linux-headers \
    libxslt-dev \
    gd-dev \
    gnupg1 \
    make \
    ncurses-dev \
    openssl-dev \
    pax-utils \
    pcre-dev \
    python3-dev \
    readline-dev \
    sqlite-dev \
    tcl-dev \
    tk \
    tk-dev \
    util-linux-dev \
    xz-dev \
    zlib-dev

COPY ./ /app

# TODO: This shouls be copied to a tmp dir first then install as a module (eg. w/o -e)
WORKDIR /app
RUN python3 -m pip install --no-cache-dir --compile -e ./ 

COPY ./config.yaml /config/config.yaml
COPY ./logging.config /config/logging.config

COPY ./entrypoint.sh /entrypoint.sh

# Final cleanup 
# TODO: some parts of the bulidng evnironment is required after (gcc and such)
# RUN apk del .build-deps 
RUN rm -rf /tmp/* /var/cache/apk/*

ENTRYPOINT ["/entrypoint.sh"]
CMD [""]