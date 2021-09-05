FROM python:3.9-buster

LABEL Name=deneb Version=1.0.1

RUN apt-get update && apt-get install -y python3-venv python3-dev

RUN mkdir /app

RUN adduser --disabled-password captain && chown -R captain /app

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8


WORKDIR /app

RUN pip install -U pip
RUN pip install poetry

COPY poetry.lock .
COPY pyproject.toml .
COPY Makefile .

USER captain

RUN make install-dev

COPY . /app
