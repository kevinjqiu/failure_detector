FROM python:3.6-alpine
RUN apk add tzdata
COPY . /app
WORKDIR /app
RUN pip install pipenv && pipenv install
RUN cp /usr/share/zoneinfo/America/Toronto /etc/localtime
CMD source $(pipenv --venv)/bin/activate && python ./node.py
