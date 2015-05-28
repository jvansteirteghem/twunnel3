# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import socket
import struct
import twunnel3.logger

from twunnel3.proxy_server import is_ipv4_address, is_ipv6_address

class SOCKS4TunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocol.connection_made")
        
        self.transport = transport
        
        address_type = 0x03
        if is_ipv4_address(self.factory.address) == True:
            address_type = 0x01
        
        request = struct.pack("!BB", 0x04, 0x01)
        
        port = self.factory.port
        
        request = request + struct.pack("!H", port)
        
        address = 0
        if address_type == 0x01:
            address = self.factory.address
            address = socket.inet_pton(socket.AF_INET, address)
            address, = struct.unpack("!I", address)
        else:
            if address_type == 0x03:
                address = 1
        
        request = request + struct.pack("!I", address)
        
        name = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"].encode()
        name = name + b"\x00"
        name_length = len(name)
        
        request = request + struct.pack("!%ds" % name_length, name)
        
        if address_type == 0x03:
            address = self.factory.address.encode()
            address = address + b"\x00"
            address_length = len(address)
            
            request = request + struct.pack("!%ds" % address_length, address)
        
        self.transport.write(request)
        
        self.data_state = 0
        
    def connection_lost(self, exception):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
    
    def process_data_state0(self):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocol.process_data_state0")
        
        data = self.data
        
        if len(data) < 8:
            return True
        
        status, = struct.unpack("!B", data[1:2])
        
        data = data[8:]
        
        if status != 0x5a:
            self.transport.close()
            
            return True
        
        self.factory.tunnel_protocol.tunnel_output_protocol__connection_made(self.transport, data)
        
        self.data = b""
        
        return True

class SOCKS4TunnelOutputProtocolFactory(object):
    def __init__(self, configuration, address, port):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.trace("SOCKS4TunnelOutputProtocolFactory.__call__")
        
        protocol = SOCKS4TunnelOutputProtocol()
        protocol.factory = self
        return protocol