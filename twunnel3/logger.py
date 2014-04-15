# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

def set_default_configuration(configuration, keys):
    if "LOGGER" in keys:
        configuration.setdefault("LOGGER", {})
        configuration["LOGGER"].setdefault("LEVEL", 0)

logger_level = 0

def configure(configuration):
    global logger_level
    
    set_default_configuration(configuration, ["LOGGER"])
    
    logger_level = configuration["LOGGER"]["LEVEL"]

def log(message_level, message):
    global logger_level
    
    if message_level <= logger_level:
        print(message)