FROM python:3.10
WORKDIR /app

## Install Firefox and other dependencies
RUN apt-get update && \
apt-get install -y firefox-esr wget gnupg build-essential rustc cargo && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Download and install GeckoDriver for ARM64
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux-aarch64.tar.gz -O /tmp/geckodriver.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    rm /tmp/geckodriver.tar.gz

# Copy the requirements.txt and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY bot.py ./

CMD [ "python3", "./bot.py"]
# RUN apt-get update
# RUN apt-get -y install xvfb
# RUN apt-get install chromium -y
# RUN apt-get install wget -y
# RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/115.0.5790.102/linux64/chromedriver-linux64.zip
# RUN apt-get install unzip -y
#RUN unzip chromedriver-linux64.zip
#RUN mv chromedriver/ /usr/bin/chromedriver/