# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import ssl as _ssl
import twunnel3.local_proxy_server
import twunnel3.local_proxy_server__socks5
import twunnel3.logger
import twunnel3.proxy_server

class SSLInputProtocolFactory(twunnel3.local_proxy_server__socks5.SOCKS5InputProtocolFactory):
    def __init__(self, configuration):
        twunnel3.logger.trace("SSLInputProtocolFactory.__init__")
        
        self.configuration = configuration
        
        configuration = {}
        configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
        configuration["LOCAL_PROXY_SERVER"] = {}
        configuration["LOCAL_PROXY_SERVER"]["TYPE"] = "SOCKS5"
        configuration["LOCAL_PROXY_SERVER"]["ADDRESS"] = self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]
        configuration["LOCAL_PROXY_SERVER"]["PORT"] = self.configuration["REMOTE_PROXY_SERVER"]["PORT"]
        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"] = []
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"].append({})
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"]
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"]
            i = i + 1
        configuration["REMOTE_PROXY_SERVERS"] = []
        
        output_protocol_connection_manager = twunnel3.local_proxy_server.OutputProtocolConnectionManager(configuration)
        
        twunnel3.local_proxy_server__socks5.SOCKS5InputProtocolFactory.__init__(self, configuration, output_protocol_connection_manager)

def create_ssl_server(configuration):
    input_protocol_factory = SSLInputProtocolFactory(configuration)
    
    ssl = _ssl.SSLContext(_ssl.PROTOCOL_SSLv23)
    ssl.options |= _ssl.OP_NO_SSLv2
    ssl.load_cert_chain(configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["FILE"], keyfile=configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"]["FILE"])
    
    return asyncio.get_event_loop().create_server(input_protocol_factory, host=configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], port=configuration["REMOTE_PROXY_SERVER"]["PORT"], ssl=ssl)