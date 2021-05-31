##!/usr/bin/env python
# Python script to monitor the status of pihole
# Author: Maximilian Krause
# Date 29.05.2021

# Define Error Logging
def printerror(ex):
	print('\033[31m' + str(ex) + '\033[0m')

def printwarning(warn):
	print('\033[33m' + str(warn) + '\033[0m')

# Load modules
import os
if not os.geteuid() == 0:
	printerror("Please run this script with sudo.")
	exit(2)

print("Welcome to PiHole Monitor!")
print("Loading modules...")

try:
	import socket
	import configparser
	import time
	from signal import signal, SIGINT
	from sys import exit
	import os.path
	from gpiozero import CPUTemperature
	from os import path
	from datetime import datetime
	import requests
	import json
	import argparse
	import lcddriver
	from urllib.request import urlopen
	import socket
except ModuleNotFoundError:
	printerror("The app could not be started.")
	printerror("Please run 'sudo ./install.sh' first.")
	exit(2)
except:
	printerror("An unknown error occured while loading modules.")
	exit(2)

# Define Var
version = 1.0
hostname = None
piholeApi = None
webtoken = None
basicInfo = None

# Check for arguments
parser = argparse.ArgumentParser()
parser.add_argument("--version", "-v", help="Prints the version", action="store_true")
parser.add_argument("--backlightoff", "-b", help="Turns off the backlight of the lcd", action="store_true")


args = parser.parse_args()
if args.version:
	print(str(version))
	exit(0)

# Load driver for LCD display
try:
	print("Loading lcd drivers...")
	display = lcddriver.lcd()

	#Check backlight option
	if args.backlightoff:
		printwarning("Option: Backlight turned off!")
		display.backlight(0)
	else:
		display.backlight(1)

	display.lcd_display_string("Loading PiHole..", 1)
	display.lcd_display_string("V " + str(version), 2)
	time.sleep(1.5)
except IOError:
	printerror("The connection to the display failed.")
	printerror("Please check your connection for all pins.")
	printerror("From bash you can run i2cdetect -y 1")

	printerror("Would you like to proceed anyway (More errors might occur)? [y/n]")
	yes = {'yes', 'y'}
	no = {'no', 'n'}
	choice = input().lower()
	if choice in yes:
		print("Will continue...")
	elif choice in no:
		print("Shutting down... Bye!")
		exit(1)
	else:
		print("Please choose yes or no")
except Exception as e:
	printerror("An unknown error occured while connecting to the lcd.")
	printerror(e)

# Define custom LCD characters
# Char generator can be found at https://omerk.github.io/lcdchargen/
fontdata1 = [
	# char(0) - Check
	[0b00000,
	0b00001,
	0b00011,
	0b10110,
	0b11100,
	0b01000,
	0b00000,
	0b00000],

	# char(1) - Block
	[0b00000,
	0b11111,
	0b10011,
	0b10101,
	0b11001,
	0b11111,
	0b00000,
	0b00000]
]
display.lcd_load_custom_chars(fontdata1)


#############
# FUNCTIONS #
#############

# Pings pihole if still up
def detectPihole():
	response = os.system("ping -c 1 " + str(hostname) + "> /dev/null")

	#check the response...
	if response == 0:
		return True
	else:
		return False


#Handles Ctrl+C
def handler(signal_received, frame):
	# Handle any cleanup here
	print()
	printwarning('SIGINT or CTRL-C detected. Please wait until the service has stopped.')
	display.lcd_clear()
	display.lcd_display_string("Manual cancel.", 1)
	display.lcd_display_string("Exiting app.", 2)
	exit(0)


# Checks for updates
def checkUpdate():
	updateUrl = "https://raw.githubusercontent.com/maxi07/PiHole-Monitoring/main/doc/version"
	try:
		f = requests.get(updateUrl)
		latestVersion = float(f.text)
		if latestVersion > version:
			printwarning("There is an update available.")
			printwarning("Head over to https://github.com/maxi07/PiHole-Monitoring to get the hottest features.")
		else:
			print("Application is running latest version " + str(version) + ".")
	except Exception as e:
		printerror("An error occured while searching for updates.")
		printerror(e)

# Read the webpassword from pihole as token
def getToken():
	with open("/etc/pihole/setupVars.conf") as origin:
		for line in origin:
			if not "WEBPASSWORD" in line:
				continue
			try:
				token = line.split('=')[1]
				token = os.linesep.join([s for s in token.splitlines() if s])
				print("Found pihole token: " + token)
				return token
			except IndexError:
				printerror("The PiHole webpassword could not be retrieved.")
				return None

# Reads the local config file. If none exists, a new one will be created.
def readConfig():
	display.lcd_display_string("Reading config", 2)
	config = configparser.ConfigParser()
	if os.path.isfile(str(os.getcwd()) + "/piholemon_config.ini"):
		print("Reading config...")
		config.read("piholemon_config.ini")

		global piholeApi
		piholeApi = config["piholemon"]["piholeApi"]
		global webtoken
		webtoken = config["piholemon"]["webtoken"]
		global hostname
		hostname = config["piholemon"]["hostname"]
		print("Config successfully loaded.")
		display.lcd_display_string("Config loaded", 2)
	else:
		printwarning("Config does not exist, creating new file.")
		webtoken = ""

		display.lcd_display_string("Creating config", 2)
		# Detect pihole system
		print("Detecting your PiHole...")
		hostname = findPihole()
		while not hostname:
			hostname = input("Please enter your PiHole address (e.g. 192.168.178.2): ")
		piholeApi = "http://" + hostname + "/admin/api.php?"

		# Detect pihole webtoken
		webtoken = getToken()
		while not webtoken:
			webtoken = input("Please enter your token for your PiHole webpassword: ")
		config["piholemon"] = {"piholeApi": piholeApi, "webtoken": webtoken, "hostname": hostname}
		with open("piholemon_config.ini", "w") as configfile:
			config.write(configfile)
			print("Stored a new config file.")
			display.lcd_display_string("Stored config  ", 2)

# Detect PiHole by hostname
def findPihole():
	try:
		ip = socket.gethostbyname('pihole')
		print("Detected PiHole system at " + ip)
		return str(ip)
	except:
		printwarning("No PiHole system could be detected.")
		return None

# Check or internet connection
def is_connected():
    try:
        # connect to the host -- tells us if the host is actually
        # reachable
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass
    return False

def clearDisplayLine(line):
	display.lcd_display_string("                ", line)


# Check if PiHole Status is enabled
def getPiholeStatus():
	if basicInfo['status'] == "enabled":
		return True
	else:
		return False

# Read basic info and store JSON
def getBasicInfo():
	global basicInfo
	try:
		r = urlopen(piholeApi)
		basicInfo = json.loads(r.read())
	except Exception as e:
		printerror("An error occured while reading API.")
		printerror(e)



# Read number of requests today
def getTodayRequest():
	return basicInfo['dns_queries_today']

# Get ad blocked today
def getTodayBlocked():
	return basicInfo['ads_blocked_today']

# Get last block from PiHole
def getLastBlock():
	try:
		url = requests.get(piholeApi + "recentBlocked&auth=" + webtoken)
		return (url.text)
	except:
		printerror("The last PiHole block could not be read.")
		return None


def wait():
	time.sleep(3) #3 seconds


def printHeader():
	os.system('clear')
	print('##########################')
	print('    PiHole Monitoring     ')
	print('##########################')
	print()
	now = datetime.now()
	print("Last API call:\t\t" + now.strftime("%Y-%m-%d %H:%M:%S"))
	print("Requests / blocked:\t" + str(getTodayRequest()) + "/" + str(getTodayBlocked()))

	cpu = CPUTemperature()
	cpu_r = round(cpu.temperature, 2)
	print("Current CPU:\t\t" + str(cpu_r) + "°C")


#Main
if __name__ == '__main__':
	# Tell Python to run the handler() function when SIGINT is recieved
	signal(SIGINT, handler)

	# Check version
	checkUpdate()

	# Read config first
	readConfig()


	if detectPihole() == True:
		clearDisplayLine(2)
		display.lcd_display_string(str(hostname), 2)
		time.sleep(1.5)
	else:
		printerror("PiHole could not be found!")


	lb = ""
	line1 = ""
	run = 0
	display.lcd_clear()
	while True:


		# Check if internet is reachable
		# Check if PiHole is reachable
		# Get basicInfo from API
		# Check if PiHole is enabled
		# Print to display

		# PiHole Enabled .
		# LastBlock

		if is_connected() == False:
			display.lcd_clear()
			display.lcd_display_string("No network.", 1)
			display.lcd_display_string("Check router.", 2)
			printHeader()
			printerror("The network cannot be reached. Please check your router.")
			wait()
			continue

		if detectPihole() == False:
			display.lcd_clear()
			display.lcd_display_string("PiHole not found", 1)
			display.lcd_display_string("Check LAN/Power.", 2)
			printHeader()
			printerror("The PiHole on " + str(hostname) + " could not be found.")
			printerror("Please check the power of your PiHole and if its connected to LAN")
			wait()
			continue

		# Now get the basic API info and store it
		getBasicInfo()

		if getPiholeStatus() == False:
			display.lcd_clear()
			display.lcd_display_string("PiHole Off", 1)
			display.lcd_display_string("Please wait...", 2)
			printHeader()
			printwarning("The PiHole was detected, but it returned that blocking is turned off.")
			printwarning("This can happen during an update of the PiHole.")
			wait()
			continue

		printHeader()

		line2 = chr(0) + " " + str(getTodayRequest()) + "  " + chr(1) + " " + str(getTodayBlocked())
		if line1 != line2:
			line1 = line2
			display.lcd_display_string(line2, 1)


#		if run == 0:
#			run = 1
#			display.lcd_display_string("PiHole enabled. ", 1)
#		else:
#			run = 0
#			display.lcd_display_string("PiHole enabled .", 1)

		nlb = getLastBlock()
		if nlb is None:
			printerror("The last block from PiHole could not be read (Returned nothing)")
			lb = "Error reading"

		print("Last block:\t\t" + nlb)

		if nlb != lb:
			lb = nlb
			clearDisplayLine(2)
			display.lcd_display_string(nlb, 2)
		wait()

