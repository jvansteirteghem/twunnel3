# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import twunnel3.proxy_server

def set_default_configuration(configuration, keys):
    twunnel3.proxy_server.set_default_configuration(configuration, keys)
    
    if "REMOTE_PROXY_SERVER" in keys:
        configuration.setdefault("REMOTE_PROXY_SERVER", {})
        configuration["REMOTE_PROXY_SERVER"].setdefault("TYPE", "")
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSL":
            configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
            configuration["REMOTE_PROXY_SERVER"].setdefault("CERTIFICATE", {})
            configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("FILE", "")
            configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("KEY", {})
            configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"].setdefault("FILE", "")
            configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
            i = 0
            while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                i = i + 1

def create_server(configuration):
    set_default_configuration(configuration, ["PROXY_SERVERS", "REMOTE_PROXY_SERVER"])
    
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSL":
        from twunnel3.remote_proxy_server__ssl import create_ssl_server
        
        return create_ssl_server(configuration)
    else:
        return None