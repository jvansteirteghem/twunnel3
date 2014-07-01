# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import asyncio
import twunnel3.logger
import twunnel3.proxy_server

def set_default_configuration(configuration, keys):
    twunnel3.proxy_server.set_default_configuration(configuration, keys)
    
    if "LOCAL_PROXY_SERVER" in keys:
        configuration.setdefault("LOCAL_PROXY_SERVER", {})
        configuration["LOCAL_PROXY_SERVER"].setdefault("TYPE", "")
        if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "HTTPS":
            configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
        else:
            if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS4":
                configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
                configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
            else:
                if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
                    configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
                    configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
                    configuration["LOCAL_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                    i = 0
                    while i < len(configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]):
                        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                        i = i + 1
    
    if "REMOTE_PROXY_SERVERS" in keys:
        configuration.setdefault("REMOTE_PROXY_SERVERS", [])
        i = 0
        while i < len(configuration["REMOTE_PROXY_SERVERS"]):
            configuration["REMOTE_PROXY_SERVERS"][i].setdefault("TYPE", "")
            if configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"] == "SSL":
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("PORT", 0)
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("CERTIFICATE", {})
                configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"].setdefault("AUTHORITY", {})
                configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"]["AUTHORITY"].setdefault("FILE", "")
                configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            i = i + 1

def create_server(configuration):
    set_default_configuration(configuration, ["PROXY_SERVERS", "LOCAL_PROXY_SERVER", "REMOTE_PROXY_SERVERS"])
    
    output_protocol_connection_manager = OutputProtocolConnectionManager(configuration)
    
    if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "HTTPS":
        from twunnel3.local_proxy_server__https import create_https_server
        
        return create_https_server(configuration, output_protocol_connection_manager)
    else:
        if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS4":
            from twunnel3.local_proxy_server__socks4 import create_socks4_server
            
            return create_socks4_server(configuration, output_protocol_connection_manager)
        else:
            if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
                from twunnel3.local_proxy_server__socks5 import create_socks5_server
                
                return create_socks5_server(configuration, output_protocol_connection_manager)
            else:
                return None

class OutputProtocol(asyncio.Protocol):
    def __init__(self):
        twunnel3.logger.log(3, "trace: OutputProtocol.__init__")
        
        self.input_protocol = None
        self.connection_state = 0
        self.transport = None
        
    def connection_made(self, transport):
        twunnel3.logger.log(3, "trace: OutputProtocol.connection_made")
        
        self.transport = transport
        
        self.connection_state = 1
        
        self.input_protocol.output_protocol__connection_made(self.transport)
        
    def connection_lost(self, exception):
        twunnel3.logger.log(3, "trace: OutputProtocol.connection_lost")
        
        self.connection_state = 2
        
        self.input_protocol.output_protocol__connection_lost(exception)
        
        self.transport = None
        
    def data_received(self, data):
        twunnel3.logger.log(3, "trace: OutputProtocol.data_received")
        
        self.input_protocol.output_protocol__data_received(data)
        
    def input_protocol__connection_made(self, transport):
        twunnel3.logger.log(3, "trace: OutputProtocol.input_protocol__connection_made")
        
    def input_protocol__connection_lost(self, exception):
        twunnel3.logger.log(3, "trace: OutputProtocol.input_protocol__connection_lost")
        
        if self.connection_state == 1:
            self.transport.close()
        
    def input_protocol__data_received(self, data):
        twunnel3.logger.log(3, "trace: OutputProtocol.input_protocol__data_received")
        
        if self.connection_state == 1:
            self.transport.write(data)
    
    def pause_writing(self):
        twunnel3.logger.log(3, "trace: OutputProtocol.pause_reading")
        
        if self.connection_state == 1:
            self.transport.pause_reading()
    
    def resume_writing(self):
        twunnel3.logger.log(3, "trace: OutputProtocol.resume_writing")
        
        if self.connection_state == 1:
            self.transport.resume_reading()

class OutputProtocolFactory(object):
    def __init__(self, input_protocol):
        twunnel3.logger.log(3, "trace: OutputProtocolFactory.__init__")
        
        self.input_protocol = input_protocol
        
    def __call__(self):
        twunnel3.logger.log(3, "trace: OutputProtocolFactory.__call__")
        
        output_protocol = OutputProtocol()
        output_protocol.input_protocol = self.input_protocol
        output_protocol.input_protocol.output_protocol = output_protocol
        return output_protocol

class OutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel3.logger.log(3, "trace: OutputProtocolConnection.__init__")
        
        self.configuration = configuration
    
    def connect(self, remote_address, remote_port, input_protocol):
        twunnel3.logger.log(3, "trace: OutputProtocolConnection.connect")
        
        output_protocol_factory = OutputProtocolFactory(input_protocol)
        
        tunnel = twunnel3.proxy_server.create_tunnel(self.configuration)
        asyncio.async(tunnel.create_connection(output_protocol_factory, address=remote_address, port=remote_port))

class OutputProtocolConnectionManager(object):
    def __init__(self, configuration):
        twunnel3.logger.log(3, "trace: OutputProtocolConnectionManager.__init__")
        
        self.configuration = configuration
        self.i = -1
        
        self.output_protocol_connections = []
        
        if len(self.configuration["REMOTE_PROXY_SERVERS"]) == 0:
            configuration = {}
            configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
            configuration["LOCAL_PROXY_SERVER"] = self.configuration["LOCAL_PROXY_SERVER"]
            
            output_protocol_connection = OutputProtocolConnection(configuration)
            self.output_protocol_connections.append(output_protocol_connection)
        else:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVERS"]):
                configuration = {}
                configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
                configuration["LOCAL_PROXY_SERVER"] = self.configuration["LOCAL_PROXY_SERVER"]
                configuration["REMOTE_PROXY_SERVER"] = self.configuration["REMOTE_PROXY_SERVERS"][i]
                
                output_protocol_connection_class = self.get_output_protocol_connection_class(configuration["REMOTE_PROXY_SERVER"]["TYPE"])
                
                if output_protocol_connection_class is not None:
                    output_protocol_connection = output_protocol_connection_class(configuration)
                    self.output_protocol_connections.append(output_protocol_connection)
                
                i = i + 1
    
    def connect(self, remote_address, remote_port, input_protocol):
        twunnel3.logger.log(3, "trace: OutputProtocolConnectionManager.connect")
        
        self.i = self.i + 1
        if self.i >= len(self.output_protocol_connections):
            self.i = 0
        
        output_protocol_connection = self.output_protocol_connections[self.i]
        output_protocol_connection.connect(remote_address, remote_port, input_protocol)
    
    def get_output_protocol_connection_class(self, type):
        twunnel3.logger.log(3, "trace: OutputProtocolConnectionManager.get_output_protocol_connection_class")
        
        if type == "SSL":
            from twunnel3.local_proxy_server__ssl import SSLOutputProtocolConnection
            
            return SSLOutputProtocolConnection
        else:
            return None