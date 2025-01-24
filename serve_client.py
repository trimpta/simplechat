"""
Run this script to serve the client.py file on the local network with the correct IP address.

Clients can now connect to the server with a single command.

Windows clients: 
    curl -s http://<ip_address>:8000/client.py -o client.py && python client.py

Linux clients:
    wget http://<ip_address>:8000/client.py && python3 client.py
"""

import socket
import http.server
import threading
import os
from server import *

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

print(f"IP Address: {ip_address}")

with open("client.py", "r") as f:
    content = f.read()
    content = content.replace("localhost", ip_address)
    
with open("out/client.py", "w") as f:
    f.write(content)

chat_server_thread = threading.Thread(target = main)
chat_server_thread.start()

os.system("python -m http.server 8000 --directory out")