FROM ghcr.io/cfpb/regtech/sbl/python-alpine:3.12

WORKDIR /usr/app
RUN mkdir reports
RUN pip install poetry

COPY poetry.lock pyproject.toml alembic.ini README.md ./

COPY ./src ./src
COPY ./db_revisions ./db_revisions

RUN poetry config virtualenvs.create false
RUN poetry install --only main

WORKDIR /usr/app/src

EXPOSE 8888

USER sbl

CMD ["python", "sbl_filing_api/main.py"]
