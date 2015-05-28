# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import ssl as _ssl
import twunnel3.local_proxy_server
import twunnel3.logger
import twunnel3.proxy_server
import twunnel3.proxy_server__socks5

class SSLOutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel3.logger.trace("SSLOutputProtocolConnection.__init__")
        
        self.configuration = configuration
    
    def connect(self, remote_address, remote_port, input_protocol):
        twunnel3.logger.trace("SSLOutputProtocolConnection.connect")
        
        configuration = {}
        configuration["PROXY_SERVER"] = {}
        configuration["PROXY_SERVER"]["TYPE"] = "SOCKS5"
        configuration["PROXY_SERVER"]["ADDRESS"] = self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]
        configuration["PROXY_SERVER"]["PORT"] = self.configuration["REMOTE_PROXY_SERVER"]["PORT"]
        configuration["PROXY_SERVER"]["ACCOUNT"] = {}
        configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"]
        configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]
        
        output_protocol_factory = twunnel3.local_proxy_server.OutputProtocolFactory(input_protocol)
        
        tunnel_output_protocol_factory = twunnel3.proxy_server__socks5.SOCKS5TunnelOutputProtocolFactory(configuration, remote_address, remote_port)
        tunnel_protocol_factory = twunnel3.proxy_server.TunnelProtocolFactory(tunnel_output_protocol_factory, output_protocol_factory, None, None)
        
        ssl = _ssl.SSLContext(_ssl.PROTOCOL_SSLv23)
        ssl.options |= _ssl.OP_NO_SSLv2
        ssl.set_default_verify_paths()
        ssl.verify_mode = _ssl.CERT_REQUIRED
        if self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["AUTHORITY"]["FILE"] != "":
            ssl.load_verify_locations(cafile=self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["AUTHORITY"]["FILE"])
        
        ssl_address = self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]
        if self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["ADDRESS"] != "":
            ssl_address = self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["ADDRESS"]
        
        tunnel = twunnel3.proxy_server.create_tunnel(self.configuration)
        asyncio.async(tunnel.create_connection(tunnel_protocol_factory, address=self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], port=self.configuration["REMOTE_PROXY_SERVER"]["PORT"], ssl=ssl, ssl_address=ssl_address))