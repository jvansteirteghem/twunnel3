# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import base64
import twunnel3.logger

from twunnel3.proxy_server import is_ipv4_address, is_ipv6_address

class HTTPSTunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
        
    def connection_made(self, transport):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocol.connection_made")
        
        self.transport = transport
        
        request = b"CONNECT "
        
        if is_ipv6_address(self.factory.address) == True:
            request = request + b"[" + self.factory.address.encode() + b"]:" + str(self.factory.port).encode()
        else:
            request = request + self.factory.address.encode() + b":" + str(self.factory.port).encode()
        
        request = request + b" HTTP/1.1\r\n"
        
        if self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"].encode() != b"":
            request = request + b"Proxy-Authorization: Basic " + base64.standard_b64encode(self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"].encode() + b":" + self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"].encode()) + b"\r\n"
        
        request = request + b"\r\n"
        
        self.transport.write(request)
        
    def connection_lost(self, exception):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
    
    def process_data_state0(self):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocol.process_data_state0")
        
        data = self.data
        
        i = data.find(b"\r\n\r\n")
        
        if i == -1:
            return True
            
        i = i + 4
        
        response = data[:i]
        
        data = data[i:]
        
        response_lines = response.split(b"\r\n")
        response_line = response_lines[0].split(b" ", 2)
        
        if len(response_line) != 3:
            self.transport.close()
            
            return True
        
        response_version = response_line[0].upper()
        response_status = response_line[1]
        response_status_message = response_line[2]
        
        if response_status != b"200":
            self.transport.close()
            
            return True
        
        self.factory.tunnel_protocol.tunnel_output_protocol__connection_made(self.transport, data)
        
        self.data = b""
        
        return True

class HTTPSTunnelOutputProtocolFactory(object):
    def __init__(self, configuration, address, port):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.trace("HTTPSTunnelOutputProtocolFactory.__call__")
        
        protocol = HTTPSTunnelOutputProtocol()
        protocol.factory = self
        return protocol