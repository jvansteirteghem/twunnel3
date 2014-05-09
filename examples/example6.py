import sys
import os
sys.path.insert(0, os.path.abspath(".."))

import asyncio
from twunnel3 import local_proxy_server, logger, remote_proxy_server
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
        "TYPE": "SOCKS5",
        "ADDRESS": "127.0.0.1",
        "PORT": 8080,
        "ACCOUNTS":
        [
            {
                "NAME": "",
                "PASSWORD": ""
            }
        ]
    },
    "REMOTE_PROXY_SERVERS":
    [
        {
            "TYPE": "SSL",
            "ADDRESS": "127.0.0.1",
            "PORT": 8443,
            "CERTIFICATE":
            {
                "AUTHORITY":
                {
                    "FILE": "files/SSL/CA.pem"
                },
                "ADDRESS": ""
            },
            "ACCOUNT":
            {
                "NAME": "",
                "PASSWORD": ""
            }
        }
    ]
}

socks5_server = loop.run_until_complete(local_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS": [],
    "REMOTE_PROXY_SERVER":
    {
        "TYPE": "SSL",
        "ADDRESS": "127.0.0.1",
        "PORT": 8443,
        "CERTIFICATE":
        {
            "FILE": "files/SSL/C.pem",
            "KEY":
            {
                "FILE": "files/SSL/CK.pem"
            }
        },
        "ACCOUNTS":
        [
            {
                "NAME": "",
                "PASSWORD": ""
            }
        ]
    }
}

ssl_server = loop.run_until_complete(remote_proxy_server.create_server(configuration))

configuration = \
{
    "PROXY_SERVERS":
    [
        {
            "TYPE": "SOCKS5",
            "ADDRESS": "127.0.0.1",
            "PORT": 8080,
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
loop.call_later(15, ssl_server.close)
loop.call_later(20, socks5_server.close)
loop.call_later(25, loop.stop)
loop.run_forever()