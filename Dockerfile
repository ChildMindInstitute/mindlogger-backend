FROM python:3.7.11
ENV PYTHONUNBUFFERED 1
ENV PROJECT_NAME app
ENV PROJECT_PATH /$PROJECT_NAME

RUN mkdir -p $PROJECT_PATH

ADD requirements.txt $PROJECT_PATH/requirements.txt

RUN apt-get update && apt-get install -y \
    git  \
    g++  \
    python3-dev  \
    libldap2-dev \
    libsasl2-dev \
    && pip3 install --no-cache-dir -r $PROJECT_PATH/requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR $PROJECT_PATH
COPY . $PROJECT_PATH/

RUN pip install --upgrade --upgrade-strategy eager --editable .

COPY ./docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]
