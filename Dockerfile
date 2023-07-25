FROM python:3.11.4-slim-bullseye
WORKDIR /app
RUN apt-get update
RUN apt-get -y install xvfb
RUN apt-get install -y wget
RUN apt-get install -y gnupg2
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install ./google-chrome-stable_current_amd64.deb
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python3", "./bot.py"]