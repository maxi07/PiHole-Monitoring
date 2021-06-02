# PiHole-Monitoring
A Python script to monitor the latest block on a lcd display. The first number represents the dns queries from the last 24h, the seconds the total blocked queries from the last 24h.
<img src="https://raw.githubusercontent.com/maxi07/PiHole-Monitoring/main/doc/lcd_display.jpg" align="center"/>

## Installation
To install clone this repository and run
```bash
sudo ./install.sh
```
The device will reboot after completed. 

## Wiring / LCD Display
The script was developed for a 16x2 I2C display, which can be found for cheap on Amazon.com.
For wiring setup, please check the [wiki.](https://github.com/maxi07/PiHole-Monitoring/wiki/Connect-LCD-display)

## Run
To run the script, execute
```bash
python3 piholeMonitoring.py
```

## Options
To print all available options, use 
```bash
python3 piholeMonitoring.py --help
```
