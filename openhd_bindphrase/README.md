# Installing

1) First, connect your Raspberry Pi to internet, line using eth0 device
2) Clone the repository
```
git clone https://github.com/SYNERHIIA/openhd_bindphrase &&
cd openhd_bindphrase
```
3) Edit apt sources.list link for update apt
```
sudo nano /etc/apt/sources.list
```
copy current settting in the file and comment it, paste text and then edit link on bellow one:
```
https://distrohub.kyiv.ua/raspbian/raspbian/
```
then save (Ctrl + X / Y)
4) Install pip
```
sudo apt update && sudo apt install python3-pip
```
5) Install python requirements
```
pip3 install -r reuirements.txt &&
sudo pip3 install dnslib
```
6) Run systemctl services
```
sudo cp fake_dns.service /etc/systemd/system/ && sudo cp bindphrase_web.service /etc/systemd/system/ &&
sudo systemctl enable ake_dns.services bindphrase_web.service
```
7) Reboot system

# Using

1) Connect to openhd_air[ground] wifi
2) Automatically open 192.168.3.1:5000

![image](https://github.com/user-attachments/assets/e8544ad0-2826-4130-9717-da2138c62b24)
