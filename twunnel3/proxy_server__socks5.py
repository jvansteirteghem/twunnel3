# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import socket
import struct
import twunnel3.logger

from twunnel3.proxy_server import is_ipv4_address, is_ipv6_address

class SOCKS5TunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.connection_made")
        
        self.transport = transport
        
        request = struct.pack("!BBBB", 0x05, 0x02, 0x00, 0x02)
        
        self.transport.write(request)
        
        self.data_state = 0
        
    def connection_lost(self, exception):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
        if self.data_state == 1:
            if self.process_data_state1():
                return
        if self.data_state == 2:
            if self.process_data_state2():
                return
        if self.data_state == 3:
            if self.process_data_state3():
                return
        
    def process_data_state0(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.process_data_state0")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, method = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        self.data = data
        
        if method == 0x00:
            self.data_state = 2
            
            return False
        else:
            if method == 0x02:
                name = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"].encode()
                name_length = len(name)
                
                password = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"].encode()
                password_length = len(password)
                
                request = struct.pack("!B", 0x01)
                request = request + struct.pack("!B%ds" % name_length, name_length, name)
                request = request + struct.pack("!B%ds" % password_length, password_length, password)
                
                self.transport.write(request)
                
                self.data_state = 1
                
                return True
            else:
                self.transport.close()
                
                return True
        
    def process_data_state1(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.process_data_state1")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, status = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        self.data = data
        
        if status != 0x00:
            self.transport.close()
            
            return True
        
        self.data_state = 2
        
        return False
        
    def process_data_state2(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.process_data_state2")
        
        address_type = 0x03
        if is_ipv4_address(self.factory.address) == True:
            address_type = 0x01
        else:
            if is_ipv6_address(self.factory.address) == True:
                address_type = 0x04
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        if address_type == 0x01:
            address = self.factory.address
            address = socket.inet_pton(socket.AF_INET, address)
            address, = struct.unpack("!I", address)
            
            request = request + struct.pack("!BI", 0x01, address)
        else:
            if address_type == 0x03:
                address = self.factory.address.encode()
                address_length = len(address)
                
                request = request + struct.pack("!BB%ds" % address_length, 0x03, address_length, address)
            else:
                if address_type == 0x04:
                    address = self.factory.address
                    address = socket.inet_pton(socket.AF_INET6, address)
                    address1, address2, address3, address4 = struct.unpack("!IIII", address)
                    
                    request = request + struct.pack("!BIIII", 0x04, address1, address2, address3, address4)
        
        port = self.factory.port
        
        request = request + struct.pack("!H", port)
        
        self.transport.write(request)
        
        self.data_state = 3
        
        return True
    
    def process_data_state3(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocol.process_data_state3")
        
        data = self.data
        
        if len(data) < 4:
            return True
        
        version, status, reserved, address_type = struct.unpack("!BBBB", data[:4])
        
        data = data[4:]
        
        if status != 0x00:
            self.transport.close()
            
            return True
        
        if address_type == 0x01:
            if len(data) < 4:
                return True
            
            address, = struct.unpack("!I", data[:4])
            address = struct.pack("!I", address)
            address = socket.inet_ntop(socket.AF_INET, address)
            
            data = data[4:]
        else:
            if address_type == 0x03:
                if len(data) < 1:
                    return True
                
                address_length, = struct.unpack("!B", data[:1])
                
                data = data[1:]
                
                if len(data) < address_length:
                    return True
                
                address, = struct.unpack("!%ds" % address_length, data[:address_length])
                
                data = data[address_length:]
            else:
                if address_type == 0x04:
                    if len(data) < 16:
                        return True
                    
                    address1, address2, address3, address4 = struct.unpack("!IIII", data[:16])
                    address = struct.pack("!IIII", address1, address2, address3, address4)
                    address = socket.inet_ntop(socket.AF_INET6, address)
                    
                    data = data[16:]
        
        if len(data) < 2:
            return True
        
        port, = struct.unpack("!H", data[:2])
        
        data = data[2:]
        
        self.factory.tunnel_protocol.tunnel_output_protocol__connection_made(self.transport, data)
        
        self.data = b""
        
        return True

class SOCKS5TunnelOutputProtocolFactory(object):
    def __init__(self, configuration, address, port):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.trace("SOCKS5TunnelOutputProtocolFactory.__call__")
        
        protocol = SOCKS5TunnelOutputProtocol()
        protocol.factory = self
        return protocol