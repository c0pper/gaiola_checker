## Deploy su rpi
Non sono stato capace di installarlo su docker, crontab non parte e non è facilmente debuggabile, [soluzione sembra essere systemd](https://stackoverflow.com/questions/67745554/autostarting-python-scripts-on-boot-using-crontab-on-rasbian):

This is what an example systemd service file, located at ```/etc/systemd/system/myscript.service```, would look like:
and then you can enable this program to run on boot with the command:

```sudo systemctl enable myscript.service```