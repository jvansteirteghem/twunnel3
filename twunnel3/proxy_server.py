# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import base64
import socket
import struct
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
        twunnel3.logger.log(3, "trace: TunnelProtocol.__init__")
        
        self.data = b""
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.log(3, "trace: TunnelProtocol.connection_made")
        
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
        twunnel3.logger.log(3, "trace: TunnelProtocol.connection_lost")
        
        if self.factory.tunnel_output_protocol is not None:
            self.factory.tunnel_output_protocol.connection_lost(exception)
        else:
            if self.factory.output_protocol is not None:
                self.factory.output_protocol.connection_lost(exception)
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: TunnelProtocol.data_received")
        
        if self.factory.tunnel_output_protocol is not None:
            self.factory.tunnel_output_protocol.data_received(data)
        else:
            if self.factory.output_protocol is not None:
                self.factory.output_protocol.data_received(data)
    
    def tunnel_output_protocol__connection_made(self, transport, data):
        twunnel3.logger.log(3, "trace: TunnelProtocol.tunnel_output_protocol__connection_made")
        
        self.data = data
        
        asyncio.async(asyncio.get_event_loop().create_connection(lambda: self, sock=self.transport.get_extra_info("socket"), ssl=self.factory.ssl, server_hostname=self.factory.ssl_address))

class TunnelProtocolFactory(object):
    def __init__(self, tunnel_output_protocol_factory, output_protocol_factory, ssl, ssl_address):
        twunnel3.logger.log(3, "trace: TunnelProtocolFactory.__init__")
        
        self.tunnel_output_protocol = None
        self.tunnel_output_protocol_factory = tunnel_output_protocol_factory
        self.output_protocol = None
        self.output_protocol_factory = output_protocol_factory
        self.ssl = ssl
        self.ssl_address = ssl_address
    
    def __call__(self):
        twunnel3.logger.log(3, "trace: TunnelProtocolFactory.__call__")
        
        protocol = TunnelProtocol()
        protocol.factory = self
        return protocol

class Tunnel(object):
    def __init__(self, configuration):
        twunnel3.logger.log(3, "trace: Tunnel.__init__")
        
        self.configuration = configuration
    
    def create_connection(self, output_protocol_factory, address=None, port=None, *, local_address=None, local_port=None, address_family=0, address_protocol=0, address_flags=0, ssl=None, ssl_address=None):
        twunnel3.logger.log(3, "trace: Tunnel.create_connection")
        
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
        twunnel3.logger.log(3, "trace: Tunnel.get_tunnel_output_protocol_factory_class")
        
        if type == "HTTPS":
            return HTTPSTunnelOutputProtocolFactory
        else:
            if type == "SOCKS4":
                return SOCKS4TunnelOutputProtocolFactory
            else:
                if type == "SOCKS5":
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

class HTTPSTunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
        
    def connection_made(self, transport):
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocol.connection_made")
        
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
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
    
    def process_data_state0(self):
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocol.process_data_state0")
        
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
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.__call__")
        
        protocol = HTTPSTunnelOutputProtocol()
        protocol.factory = self
        return protocol

class SOCKS4TunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.connection_made")
        
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
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.data_received")
        
        self.data = self.data + data
        if self.data_state == 0:
            if self.process_data_state0():
                return
    
    def process_data_state0(self):
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.process_data_state0")
        
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
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.__call__")
        
        protocol = SOCKS4TunnelOutputProtocol()
        protocol.factory = self
        return protocol

class SOCKS5TunnelOutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = b""
        self.data_state = 0
        self.factory = None
        self.transport = None
    
    def connection_made(self, transport):
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connection_made")
        
        self.transport = transport
        
        request = struct.pack("!BBBB", 0x05, 0x02, 0x00, 0x02)
        
        self.transport.write(request)
        
        self.data_state = 0
        
    def connection_lost(self, exception):
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connection_lost")
        
        self.transport = None
    
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.data_received")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.process_data_state0")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.process_data_state1")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.process_data_state2")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.process_data_state3")
        
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
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnel_protocol = None
    
    def __call__(self):
        twunnel3.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.__call__")
        
        protocol = SOCKS5TunnelOutputProtocol()
        protocol.factory = self
        return protocol