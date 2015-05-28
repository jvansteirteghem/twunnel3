# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import time
import datetime

class LoggerMessage(object):
    def __init__(self):
        self.time = 0
        self.level = 0
        self.text = ""

class Logger(object):
    def __init__(self, configuration):
        self.configuration = configuration
    
    def log(self, message_level, message_text, *message_text_arguments):
        if message_level <= self.configuration["LOGGER"]["LEVEL"]:
            message = LoggerMessage()
            message.time = int(round(time.time() * 1000))
            message.level = message_level
            message.text = message_text.format(*message_text_arguments)
            
            self.print_message(message)
    
    def print_message(self, message):
        print(self.format_message(message))
    
    def format_message(self, message):
        return "{0} - {1} - {2}".format(self.format_message_time(message.time), self.format_message_level(message.level), self.format_message_text(message.text))
    
    def format_message_time(self, message_time):
        return datetime.datetime.utcfromtimestamp(message_time / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")
    
    def format_message_level(self, message_level):
        if message_level == 1:
            return "ERROR"
        elif message_level == 2:
            return "WARNING"
        elif message_level == 3:
            return "INFO"
        elif message_level == 4:
            return "DEBUG"
        elif message_level == 5:
            return "TRACE"
        else:
            return ""
    
    def format_message_text(self, message_text):
        return message_text

default_logger = None
default_logger_class = Logger

def get_default_logger_class():
    global default_logger_class
    
    return default_logger_class

def set_default_logger_class(logger_class):
    global default_logger_class
    
    default_logger_class = logger_class

def set_default_configuration(configuration, keys):
    if "LOGGER" in keys:
        configuration.setdefault("LOGGER", {})
        configuration["LOGGER"].setdefault("LEVEL", 0)

def configure(configuration):
    global default_logger, default_logger_class
    
    set_default_configuration(configuration, ["LOGGER"])
    
    default_logger = default_logger_class(configuration)

def log(message_level, message_text, *message_text_arguments):
    global default_logger
    
    if default_logger is None:
        configuration = {}
        configure(configuration)
    
    default_logger.log(message_level, message_text, *message_text_arguments)

def error(message_text, *message_text_arguments):
    log(1, message_text, *message_text_arguments)

def warning(message_text, *message_text_arguments):
    log(2, message_text, *message_text_arguments)

def info(message_text, *message_text_arguments):
    log(3, message_text, *message_text_arguments)

def debug(message_text, *message_text_arguments):
    log(4, message_text, *message_text_arguments)

def trace(message_text, *message_text_arguments):
    log(5, message_text, *message_text_arguments)