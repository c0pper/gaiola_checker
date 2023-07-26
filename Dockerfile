FROM python:3.11.4-slim-bullseye
WORKDIR /app
RUN apt-get update
RUN apt-get -y install xvfb
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python3", "./bot.py"]