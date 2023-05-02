FROM python:3.7-alpine

RUN apk update

# required for lxml
RUN apk add libxml2-dev libxslt-dev

# required for psycopg2
RUN apk add gcc musl-dev postgresql-dev

WORKDIR /backend

RUN pip install --upgrade pip
COPY ./requirements.txt /backend/
RUN pip install -r requirements.txt

RUN apk add wget unzip
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/93.0.4577.15/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/
ENV PATH="/usr/local/bin:$PATH"

COPY . /backend/