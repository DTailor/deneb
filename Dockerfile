FROM alpine:latest

LABEL Name=deneb Version=0.0.1

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev zeromq-dev openssl-dev libffi-dev gcc

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

WORKDIR /app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade pipenv
RUN pipenv --python 3.7

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --verbose

COPY . /app

CMD [ "pipenv",  "run", "python", "-m", "deneb"]
