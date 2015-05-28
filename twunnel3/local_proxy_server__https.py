# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import twunnel3.logger

class HTTPSInputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.trace("HTTPSInputProtocol.__init__")
        
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
        twunnel3.logger.trace("HTTPSInputProtocol.connection_made")
        
        self.transport = transport
        
        self.connection_state = 1
    
    def connection_lost(self, exception):
        twunnel3.logger.trace("HTTPSInputProtocol.connection_lost")
        
        self.connection_state = 2
        
        if self.output_protocol is not None:
            self.output_protocol.input_protocol__connection_lost(exception)
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.trace("HTTPSInputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
        if self.data_state == 1:
            if self.process_data_state1():
                return
    
    def process_data_state0(self):
        twunnel3.logger.trace("HTTPSInputProtocol.process_data_state0")
        
        data = self.data
        
        i = data.find(b"\r\n\r\n")
        
        if i == -1:
            return True
        
        i = i + 4
        
        request = data[:i]
        
        data = data[i:]
        
        self.data = data
        
        request_lines = request.split(b"\r\n")
        request_line = request_lines[0].split(b" ", 2)
        
        if len(request_line) != 3:
            response = b"HTTP/1.1 400 Bad Request\r\n"
            response = response + b"\r\n"
            
            self.transport.write(response)
            self.transport.close()
            
            return True
        
        request_method = request_line[0].upper()
        request_uri = request_line[1]
        request_version = request_line[2].upper()
        
        if request_method == b"CONNECT":
            address = b""
            port = 0
            
            i1 = request_uri.find(b"[")
            i2 = request_uri.find(b"]")
            i3 = request_uri.rfind(b":")
            
            if i3 > i2:
                address = request_uri[:i3]
                port = int(request_uri[i3 + 1:])
            else:
                address = request_uri
                port = 443
            
            if i2 > i1:
                address = address[i1 + 1:i2]
            
            self.remote_address = address.decode()
            self.remote_port = port
            
            twunnel3.logger.debug("remote_address: " + self.remote_address)
            twunnel3.logger.debug("remote_port: " + str(self.remote_port))
            
            self.output_protocol_connection_manager.connect(self.remote_address, self.remote_port, self)
            
            return True
        else:
            response = b"HTTP/1.1 405 Method Not Allowed\r\n"
            response = response + b"Allow: CONNECT\r\n"
            response = response + b"\r\n"
            
            self.transport.write(response)
            self.transport.close()
            
            return True
        
    def process_data_state1(self):
        twunnel3.logger.trace("HTTPSInputProtocol.process_data_state1")
        
        self.output_protocol.input_protocol__data_received(self.data)
        
        self.data = b""
        
        return True
        
    def output_protocol__connection_made(self, transport):
        twunnel3.logger.trace("HTTPSInputProtocol.output_protocol__connection_made")
        
        if self.connection_state == 1:
            response = b"HTTP/1.1 200 OK\r\n"
            response = response + b"\r\n"
            
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
        twunnel3.logger.trace("HTTPSInputProtocol.output_protocol__connection_lost")
        
        if self.connection_state == 1:
            if self.data_state == 1:
                self.transport.close()
            else:
                response = b"HTTP/1.1 404 Not Found\r\n"
                response = response + b"\r\n"
                
                self.transport.write(response)
                self.transport.close()
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
        
    def output_protocol__data_received(self, data):
        twunnel3.logger.trace("HTTPSInputProtocol.output_protocol__data_received")
        
        if self.connection_state == 1:
            self.transport.write(data)
        else:
            if self.connection_state == 2:
                self.output_protocol.input_protocol__connection_lost(None)
    
    def pause_writing(self):
        twunnel3.logger.trace("HTTPSInputProtocol.pause_reading")
        
        if self.connection_state == 1:
            self.transport.pause_reading()
    
    def resume_writing(self):
        twunnel3.logger.trace("HTTPSInputProtocol.resume_writing")
        
        if self.connection_state == 1:
            self.transport.resume_reading()

class HTTPSInputProtocolFactory(object):
    protocol = HTTPSInputProtocol
    
    def __init__(self, configuration, output_protocol_connection_manager):
        twunnel3.logger.trace("HTTPSInputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.output_protocol_connection_manager = output_protocol_connection_manager
    
    def __call__(self):
        twunnel3.logger.trace("HTTPSInputProtocolFactory.__call__")
        
        input_protocol = HTTPSInputProtocol()
        input_protocol.configuration = self.configuration
        input_protocol.output_protocol_connection_manager = self.output_protocol_connection_manager
        return input_protocol

def create_https_server(configuration, output_protocol_connection_manager):
    input_protocol_factory = HTTPSInputProtocolFactory(configuration, output_protocol_connection_manager)
    return asyncio.get_event_loop().create_server(input_protocol_factory, host=configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], port=configuration["LOCAL_PROXY_SERVER"]["PORT"])