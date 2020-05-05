FROM python:3.8.2-buster

LABEL Name=deneb Version=1.0.0

RUN apt-get update && apt-get install -y python3-venv python3-dev

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

WORKDIR /app

RUN pip install -U pip
RUN pip install poetry

COPY poetry.lock .
COPY pyproject.toml .
COPY Makefile .

RUN make install-dev

COPY . /app
