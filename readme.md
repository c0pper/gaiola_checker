## Deploy su rpi
Non sono stato capace di installarlo su docker, crontab non parte e non è facilmente debuggabile, [soluzione sembra essere systemd](https://stackoverflow.com/questions/67745554/autostarting-python-scripts-on-boot-using-crontab-on-rasbian):

This is what an example systemd service file, located at ```/etc/systemd/system/myscript.service```, would look like:
and then you can enable this program to run on boot with the command:

```sudo systemctl enable myscript.service```

```sudo cp gaiola_checker.service /etc/systemd/system/gaiola_checker.service && sudo systemctl enable gaiola_checker.service```


## Docker

docker build --network=host -t gaiola-checker . && docker run -it --rm --network=host --env-file .env gaiola-checker
