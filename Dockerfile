FROM python:3.11

WORKDIR /app

COPY pyproject.toml .

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

COPY . .

CMD [ "streamlit", "run", "demo.py" ]