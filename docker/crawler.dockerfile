FROM python:3.7.5
COPY / /crawler
WORKDIR /crawler

RUN pip install --no-cache-dir -r requirements.txt
