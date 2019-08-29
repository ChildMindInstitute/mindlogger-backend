FROM node:8-stretch
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

EXPOSE 8080

RUN mkdir /girderformindlogger

RUN apt-get update && apt-get install -qy \
    gcc \
    libpython2.7-dev \
    git \
    libldap2-dev \
    libsasl2-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py

WORKDIR /girderformindlogger
COPY . /girderformindlogger/

# TODO: Do we want to create editable installs of plugins as well?  We
# will need a plugin only requirements file for this.
RUN pip install --upgrade --upgrade-strategy eager --editable .
RUN girderformindlogger build

ENTRYPOINT ["girderformindlogger", "serve"]
