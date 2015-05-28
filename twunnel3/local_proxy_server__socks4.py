# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import socket
import struct
import twunnel3.logger

class SOCKS4InputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("SOCKS4InputProtocol.__init__")
        
        self.configuration = None
        self.output_protocol_connection_manager = None
        self.output_protocol = None
        self.remote_address = ""
        self.remote_port = 0
        self.connection_state = 0
        self.data = b""
        self.data_state = 0
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.trace("SOCKS4InputProtocol.connection_made")
        
        self.transport = transport
        
        self.connection_state = 1
    
    def connection_lost(self, exception):
        twunnel3.logger.trace("SOCKS4InputProtocol.connection_lost")
        
        self.connection_state = 2
        
        if self.output_protocol is not None:
            self.output_protocol.input_protocol__connection_lost(exception)
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("SOCKS4InputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
        if self.data_state == 1:
            if self.process_data_state1():
                return
        
    def process_data_state0(self):
        twunnel3.logger.trace("SOCKS4InputProtocol.process_data_state0")
        
        data = self.data
        
        if len(data) < 8:
            return True
        
        version, method, port, address = struct.unpack("!BBHI", data[:8])
        
        data = data[8:]
        
        address_type = 0x01
        if address >= 1 and address <= 255:
            address_type = 0x03
        
        self.remote_port = port
        
        if address_type == 0x01:
            address = struct.pack("!I", address)
            address = socket.inet_ntop(socket.AF_INET, address)
            
            self.remote_address = address
        
        if b"\x00" not in data:
            return True
        
        name, data = data.split(b"\x00", 1)
        
        if address_type == 0x03:
            if b"\x00" not in data:
                return True
            
            address, data = data.split(b"\x00", 1)
            
            self.remote_address = address.decode()
        
        self.data = data
        
        twunnel3.logger.debug("remote_address: " + self.remote_address)
        twunnel3.logger.debug("remote_port: " + str(self.remote_port))
        
        if method == 0x01:
            self.output_protocol_connection_manager.connect(self.remote_address, self.remote_port, self)
            
            return True
        else:
            response = struct.pack("!BBHI", 0x00, 0x5b, 0, 0)
            
            self.transport.write(response)
            self.transport.close()
            
            return True
        
    def process_data_state1(self):
        twunnel3.logger.trace("SOCKS4InputProtocol.process_data_state1")
        
        self.output_protocol.input_protocol__data_received(self.data)
        
        self.data = b""
        
        return True
        
    def output_protocol__connection_made(self, transport):
        twunnel3.logger.trace("SOCKS4InputProtocol.output_protocol__connection_made")
        
        if self.connection_state == 1:
            response = struct.pack("!BBHI", 0x00, 0x5a, 0, 0)
            
            self.transport.write(response)
            
            self.output_protocol.input_protocol__connection_made(self.transport)
            if len(self.data) > 0:
                self.output_protocol.input_protocol__data_received(self.data)
            
            self.data = b""
            self.data_state = 1
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
    
    def output_protocol__connection_lost(self, exception):
        twunnel3.logger.trace("SOCKS4InputProtocol.output_protocol__connection_lost")
        
        if self.connection_state == 1:
            if self.data_state != 1:
                response = struct.pack("!BBHI", 0x00, 0x5b, 0, 0)
                
                self.transport.write(response)
                self.transport.close()
            else:
                self.transport.close()
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
        
    def output_protocol__data_received(self, data):
        twunnel3.logger.trace("SOCKS4InputProtocol.output_protocol__data_received")
        
        if self.connection_state == 1:
            self.transport.write(data)
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
    
    def pause_writing(self):
        twunnel3.logger.trace("SOCKS4InputProtocol.pause_reading")
        
        if self.connection_state == 1:
            self.transport.pause_reading()
    
    def resume_writing(self):
        twunnel3.logger.trace("SOCKS4InputProtocol.resume_writing")
        
        if self.connection_state == 1:
            self.transport.resume_reading()

class SOCKS4InputProtocolFactory(object):
    def __init__(self, configuration, output_protocol_connection_manager):
        twunnel3.logger.trace("SOCKS4InputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.output_protocol_connection_manager = output_protocol_connection_manager
    
    def __call__(self):
        twunnel3.logger.trace("SOCKS4InputProtocolFactory.__call__")
        
        input_protocol = SOCKS4InputProtocol()
        input_protocol.configuration = self.configuration
        input_protocol.output_protocol_connection_manager = self.output_protocol_connection_manager
        return input_protocol

def create_socks4_server(configuration, output_protocol_connection_manager):
    input_protocol_factory = SOCKS4InputProtocolFactory(configuration, output_protocol_connection_manager)
    return asyncio.get_event_loop().create_server(input_protocol_factory, host=configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], port=configuration["LOCAL_PROXY_SERVER"]["PORT"])