import os
import json

if os.environ.get('COMPUTERNAME')=='CAPTAIN2020':
    # with open(r'C:\Users\captian2020\Documents\config_files\config_whatSticksApi02.json') as config_file:
    with open(r'C:\Users\captian2020\Documents\config_files\config_wsh06api.json') as config_file:
        config = json.load(config_file)
elif os.environ.get('TERM_PROGRAM')=='Apple_Terminal':
    with open('/Users/nick/Documents/_config_files/config_wsh06api.json') as config_file:
        config = json.load(config_file)
else:
    with open('/home/ubuntu/environments/config_wsh06api.json') as config_file:
        config = json.load(config_file)



class ConfigDev:
    DEBUG = True
    SECRET_KEY = config.get('SECRET_KEY')
    SQL_URI = config.get('SQL_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    WEATHER_API_KEY = config.get('WEATHER_API_KEY')
    WSH_API_PASSWORD = config.get('WSH_API_PASSWORD')

class ConfigDev:
    DEBUG = False
    SECRET_KEY = config.get('SECRET_KEY')
    SQL_URI = config.get('SQL_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    WEATHER_API_KEY = config.get('WEATHER_API_KEY')
    WSH_API_PASSWORD = config.get('WSH_API_PASSWORD')