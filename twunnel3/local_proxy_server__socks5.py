# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import socket
import struct
import twunnel3.logger

class SOCKS5InputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.__init__")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.connection_made")
        
        self.transport = transport
        
        self.connection_state = 1
    
    def connection_lost(self, exception):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.connection_lost")
        
        self.connection_state = 2
        
        if self.output_protocol is not None:
            self.output_protocol.input_protocol__connection_lost(exception)
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.data_received")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.process_data_state0")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, number_of_methods = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        if len(data) < number_of_methods:
            return True
        
        methods = struct.unpack("!%dB" % number_of_methods, data[:number_of_methods])
        
        data = data[number_of_methods:]
        
        self.data = data
        
        supported_methods = []
        if len(self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            supported_methods.append(0x00)
        else:
            supported_methods.append(0x02)
        
        for supported_method in supported_methods:
            if supported_method in methods:
                if supported_method == 0x00:
                    response = struct.pack("!BB", 0x05, 0x00)
                    
                    self.transport.write(response)
                    
                    self.data_state = 2
                    
                    return False
                else:
                    if supported_method == 0x02:
                        response = struct.pack("!BB", 0x05, 0x02)
                        
                        self.transport.write(response)
                        
                        self.data_state = 1
                        
                        return True
        
        response = struct.pack("!BB", 0x05, 0xFF)
        
        self.transport.write(response)
        self.transport.close()
        
        return True
        
    def process_data_state1(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.process_data_state1")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, name_length = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        if len(data) < name_length:
            return True
        
        name, = struct.unpack("!%ds" % name_length, data[:name_length])
        
        data = data[name_length:]
        
        if len(data) < 1:
            return True
        
        password_length, = struct.unpack("!B", data[:1])
        
        data = data[1:]
        
        if len(data) < password_length:
            return True
        
        password, = struct.unpack("!%ds" % password_length, data[:password_length])
        
        data = data[password_length:]
        
        self.data = data
        
        i = 0
        while i < len(self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]):
            if self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"].encode() == name:
                if self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"].encode() == password:
                    response = struct.pack("!BB", 0x05, 0x00)
                    
                    self.transport.write(response)
                    
                    self.data_state = 2
                    
                    return True
                
                response = struct.pack("!BB", 0x05, 0x01)
                
                self.transport.write(response)
                self.transport.close()
                
                return True
            
            i = i + 1
        
        response = struct.pack("!BB", 0x05, 0x01)
        
        self.transport.write(response)
        self.transport.close()
        
        return True
        
    def process_data_state2(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.process_data_state2")
        
        data = self.data
        
        if len(data) < 4:
            return True
        
        version, method, reserved, address_type = struct.unpack("!BBBB", data[:4])
        
        data = data[4:]
        
        if address_type == 0x01:
            if len(data) < 4:
                return True
            
            address, = struct.unpack("!I", data[:4])
            address = struct.pack("!I", address)
            address = socket.inet_ntop(socket.AF_INET, address)
            
            self.remote_address = address
            
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
                
                self.remote_address = address.decode()
                
                data = data[address_length:]
            else:
                if address_type == 0x04:
                    if len(data) < 16:
                        return True
                    
                    address1, address2, address3, address4 = struct.unpack("!IIII", data[:16])
                    address = struct.pack("!IIII", address1, address2, address3, address4)
                    address = socket.inet_ntop(socket.AF_INET6, address)
                    
                    self.remote_address = address
                    
                    data = data[16:]
        
        if len(data) < 2:
            return True
        
        port, = struct.unpack("!H", data[:2])
        
        self.remote_port = port
        
        data = data[2:]
        
        self.data = data
        
        twunnel3.logger.log(2, "remote_address: " + self.remote_address)
        twunnel3.logger.log(2, "remote_port: " + str(self.remote_port))
        
        if method == 0x01:
            self.output_protocol_connection_manager.connect(self.remote_address, self.remote_port, self)
            
            return True
        else:
            response = struct.pack("!BBBBIH", 0x05, 0x07, 0x00, 0x01, 0, 0)
            
            self.transport.write(response)
            self.transport.close()
            
            return True
        
    def process_data_state3(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.process_data_state3")
        
        self.output_protocol.input_protocol__data_received(self.data)
        
        self.data = b""
        
        return True
        
    def output_protocol__connection_made(self, transport):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.output_protocol__connection_made")
        
        if self.connection_state == 1:
            response = struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0)
            
            self.transport.write(response)
            
            self.output_protocol.input_protocol__connection_made(self.transport)
            if len(self.data) > 0:
                self.output_protocol.input_protocol__data_received(self.data)
            
            self.data = b""
            self.data_state = 3
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
        
    def output_protocol__connection_lost(self, exception):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.output_protocol__connection_lost")
        
        if self.connection_state == 1:
            if self.data_state != 3:
                response = struct.pack("!BBBBIH", 0x05, 0x05, 0x00, 0x01, 0, 0)
                
                self.transport.write(response)
                self.transport.close()
            else:
                self.transport.close()
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
        
    def output_protocol__data_received(self, data):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.output_protocol__data_received")
        
        if self.connection_state == 1:
            self.transport.write(data)
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
    
    def pause_writing(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.pause_reading")
        
        if self.connection_state == 1:
            self.transport.pause_reading()
    
    def resume_writing(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocol.resume_writing")
        
        if self.connection_state == 1:
            self.transport.resume_reading()

class SOCKS5InputProtocolFactory(object):
    def __init__(self, configuration, output_protocol_connection_manager):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.output_protocol_connection_manager = output_protocol_connection_manager
    
    def __call__(self):
        twunnel3.logger.log(3, "trace: SOCKS5InputProtocolFactory.__call__")
        
        input_protocol = SOCKS5InputProtocol()
        input_protocol.configuration = self.configuration
        input_protocol.output_protocol_connection_manager = self.output_protocol_connection_manager
        return input_protocol

def create_socks5_server(configuration, output_protocol_connection_manager):
    input_protocol_factory = SOCKS5InputProtocolFactory(configuration, output_protocol_connection_manager)
    return asyncio.get_event_loop().create_server(input_protocol_factory, host=configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], port=configuration["LOCAL_PROXY_SERVER"]["PORT"])