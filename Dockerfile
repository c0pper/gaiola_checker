FROM python:3.10
WORKDIR /app

## Install Firefox and other dependencies
RUN apt-get update && \
apt-get install -y firefox-esr wget gnupg build-essential rustc cargo && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Build and install GeckoDriver for ARM
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && \
source $HOME/.cargo/env && \
git clone https://github.com/mozilla/geckodriver.git && \
cd geckodriver && \
cargo build --release && \
cp target/release/geckodriver /usr/local/bin/ && \
cd .. && \
rm -rf geckodriver

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