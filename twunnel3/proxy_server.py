# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import socket
import twunnel3.logger

def is_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except socket.error:
        return False
    return True

def is_ipv6_address(address):
    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:
        return False
    return True

def set_default_configuration(configuration, keys):
    if "PROXY_SERVERS" in keys:
        configuration.setdefault("PROXY_SERVERS", [])
        i = 0
        while i < len(configuration["PROXY_SERVERS"]):
            configuration["PROXY_SERVERS"][i].setdefault("TYPE", "")
            if configuration["PROXY_SERVERS"][i]["TYPE"] == "HTTPS":
                configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            else:
                if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS4":
                    configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                else:
                    if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS5":
                        configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                        configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                        configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                        configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                        configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            i = i + 1

class TunnelProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("TunnelProtocol.__init__")
        
        self.data = b""
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.trace("TunnelProtocol.connection_made")
        
        self.transport = transport
        
        if self.factory.tunnel_output_protocol is None:
            self.factory.tunnel_output_protocol_factory.tunnel_protocol = self
            self.factory.tunnel_output_protocol = self.factory.tunnel_output_protocol_factory()
            self.factory.tunnel_output_protocol.connection_made(self.transport)
        else:
            if self.factory.output_protocol is None:
                self.factory.tunnel_output_protocol = None
                
                self.factory.output_protocol = self.factory.output_protocol_factory()
                self.factory.output_protocol.connection_made(self.transport)
                
                if len(self.data) > 0:
                    self.factory.output_protocol.data_received(self.data)
                    
                    self.data = b""
    
    def connection_lost(self, exception):
        twunnel3.logger.trace("TunnelProtocol.connection_lost")
        
        if self.factory.tunnel_output_protocol is not None:
            self.factory.tunnel_output_protocol.connection_lost(exception)
        else:
            if self.factory.output_protocol is not None:
                self.factory.output_protocol.connection_lost(exception)
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("TunnelProtocol.data_received")
        
        if self.factory.tunnel_output_protocol is not None:
            self.factory.tunnel_output_protocol.data_received(data)
        else:
            if self.factory.output_protocol is not None:
                self.factory.output_protocol.data_received(data)
    
    def tunnel_output_protocol__connection_made(self, transport, data):
        twunnel3.logger.trace("TunnelProtocol.tunnel_output_protocol__connection_made")
        
        self.data = data
        
        asyncio.async(asyncio.get_event_loop().create_connection(lambda: self, sock=self.transport.get_extra_info("socket"), ssl=self.factory.ssl, server_hostname=self.factory.ssl_address))

class TunnelProtocolFactory(object):
    def __init__(self, tunnel_output_protocol_factory, output_protocol_factory, ssl, ssl_address):
        twunnel3.logger.trace("TunnelProtocolFactory.__init__")
        
        self.tunnel_output_protocol = None
        self.tunnel_output_protocol_factory = tunnel_output_protocol_factory
        self.output_protocol = None
        self.output_protocol_factory = output_protocol_factory
        self.ssl = ssl
        self.ssl_address = ssl_address
    
    def __call__(self):
        twunnel3.logger.trace("TunnelProtocolFactory.__call__")
        
        protocol = TunnelProtocol()
        protocol.factory = self
        return protocol

class Tunnel(object):
    def __init__(self, configuration):
        twunnel3.logger.trace("Tunnel.__init__")
        
        self.configuration = configuration
    
    def create_connection(self, output_protocol_factory, address=None, port=None, *, local_address=None, local_port=None, address_family=0, address_protocol=0, address_flags=0, ssl=None, ssl_address=None):
        twunnel3.logger.trace("Tunnel.create_connection")
        
        local_address_port = None
        if local_address is not None or local_port is not None:
            local_address_port = (local_address, local_port)
        
        if ssl and not ssl_address:
            ssl_address = address
        
        if len(self.configuration["PROXY_SERVERS"]) == 0:
            return asyncio.get_event_loop().create_connection(output_protocol_factory, host=address, port=port, local_addr=local_address_port, family=address_family, proto=address_protocol, flags=address_flags, ssl=ssl, server_hostname=ssl_address)
        else:
            i = len(self.configuration["PROXY_SERVERS"])
            
            configuration = {}
            configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
            
            tunnel_output_protocol_factory_class = self.get_tunnel_output_protocol_factory_class(configuration["PROXY_SERVER"]["TYPE"])
            tunnel_output_protocol_factory = tunnel_output_protocol_factory_class(configuration, address, port)
            
            tunnel_protocol_factory = TunnelProtocolFactory(tunnel_output_protocol_factory, output_protocol_factory, ssl, ssl_address)
            
            i = i - 1
            
            while i > 0:
                configuration = {}
                configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
                
                tunnel_output_protocol_factory_class = self.get_tunnel_output_protocol_factory_class(configuration["PROXY_SERVER"]["TYPE"])
                tunnel_output_protocol_factory = tunnel_output_protocol_factory_class(configuration, self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"])
                
                tunnel_protocol_factory = TunnelProtocolFactory(tunnel_output_protocol_factory, tunnel_protocol_factory, None, None)
                
                i = i - 1
            
            return asyncio.get_event_loop().create_connection(tunnel_protocol_factory, host=self.configuration["PROXY_SERVERS"][i]["ADDRESS"], port=self.configuration["PROXY_SERVERS"][i]["PORT"], local_addr=local_address_port, family=address_family, proto=address_protocol, flags=address_flags)
    
    def get_tunnel_output_protocol_factory_class(self, type):
        twunnel3.logger.trace("Tunnel.get_tunnel_output_protocol_factory_class")
        
        if type == "HTTPS":
            from twunnel3.proxy_server__https import HTTPSTunnelOutputProtocolFactory
            
            return HTTPSTunnelOutputProtocolFactory
        else:
            if type == "SOCKS4":
                from twunnel3.proxy_server__socks4 import SOCKS4TunnelOutputProtocolFactory
                
                return SOCKS4TunnelOutputProtocolFactory
            else:
                if type == "SOCKS5":
                    from twunnel3.proxy_server__socks5 import SOCKS5TunnelOutputProtocolFactory
                    
                    return SOCKS5TunnelOutputProtocolFactory
                else:
                    return None

default_tunnel_class = Tunnel

def get_default_tunnel_class():
    global default_tunnel_class
    
    return default_tunnel_class

def set_default_tunnel_class(tunnel_class):
    global default_tunnel_class
    
    default_tunnel_class = tunnel_class

def create_tunnel(configuration):
    set_default_configuration(configuration, ["PROXY_SERVERS"])
    
    tunnel_class = get_default_tunnel_class()
    tunnel = tunnel_class(configuration)
    
    return tunnel