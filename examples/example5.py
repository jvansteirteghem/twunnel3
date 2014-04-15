import sys
import os
sys.path.insert(0, os.path.abspath(".."))

import asyncio
from twunnel3 import local_proxy_server, logger
from examples import example

configuration = \
{
    "LOGGER":
    {
        "LEVEL": 3
    }
}

logger.configure(configuration)

loop = asyncio.get_event_loop()

configuration = \
{
    "PROXY_SERVERS": [],
    "LOCAL_PROXY_SERVER":
    {
        "TYPE": "HTTPS",
        "ADDRESS": "127.0.0.1",
        "PORT": 8080
    }
}

https_server = loop.run_until_complete(local_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS": [],
    "LOCAL_PROXY_SERVER":
    {
        "TYPE": "SOCKS4",
        "ADDRESS": "127.0.0.1",
        "PORT": 8081
    }
}

socks4_server = loop.run_until_complete(local_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS": [],
    "LOCAL_PROXY_SERVER":
    {
        "TYPE": "SOCKS5",
        "ADDRESS": "127.0.0.1",
        "PORT": 8082,
        "ACCOUNTS":
        [
            {
                "NAME": "",
                "PASSWORD": ""
            }
        ]
    }
}

socks5_server = loop.run_until_complete(local_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS":
    [
        {
            "TYPE": "HTTPS",
            "ADDRESS": "127.0.0.1",
            "PORT": 8080,
            "ACCOUNT":
            {
                "NAME": "",
                "PASSWORD": ""
            }
        },
        {
            "TYPE": "SOCKS4",
            "ADDRESS": "127.0.0.1",
            "PORT": 8081,
            "ACCOUNT":
            {
                "NAME": ""
            }
        },
        {
            "TYPE": "SOCKS5",
            "ADDRESS": "127.0.0.1",
            "PORT": 8082,
            "ACCOUNT":
            {
                "NAME": "",
                "PASSWORD": ""
            }
        }
    ]
}

loop.call_later(5, example.create_connection, configuration)
loop.call_later(10, example.create_connection, configuration, True)
loop.call_later(15, socks5_server.close)
loop.call_later(20, socks4_server.close)
loop.call_later(25, https_server.close)
loop.call_later(30, loop.stop)
loop.run_forever()