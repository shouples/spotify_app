FROM python:latest

RUN pip install poetry

COPY ./pyproject.toml .
COPY ./poetry.lock .
COPY ./poetry.toml .
RUN poetry install

WORKDIR /apps