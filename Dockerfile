FROM python:3.11.4-slim-bullseye
WORKDIR /app
RUN apt-get update
RUN apt-get -y install xvfb
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
RUN apt install ./google-chrome-stable_current_amd64.deb
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/115.0.5790.102/linux64/chromedriver-linux64.zip
RUN unzip chromedriver_linux64.zip
RUN mv chromedriver /usr/bin/chromedriver
CMD [ "python3", "./bot.py"]