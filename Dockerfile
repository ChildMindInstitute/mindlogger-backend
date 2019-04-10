FROM node:8-stretch
MAINTAINER Kitware, Inc. <kitware@kitware.com>

EXPOSE 8080

RUN mkdir /girder
RUN mkdir /girder/logs

RUN apt-get update && apt-get install -qy \
    gcc \
    libpython2.7-dev \
    git \
    libldap2-dev \
    libsasl2-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py

WORKDIR /girder
COPY girder /girder/girder
COPY clients /girder/clients
COPY plugins /girder/plugins
COPY scripts /girder/scripts
COPY grunt_tasks /girder/grunt_tasks
COPY Gruntfile.js /girder/Gruntfile.js
COPY setup.py /girder/setup.py
COPY package.json /girder/package.json
COPY README.rst /girder/README.rst

RUN pip install --upgrade --upgrade-strategy eager --editable .[plugins]
RUN girder-install web --all-plugins

ENTRYPOINT ["girder", "serve"]