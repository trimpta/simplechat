import socket
import threading
import os
from server import *

linux_command = "wget http://{}:8000/client.py && python3 client.py"
windows_command = "curl http://{}:8000/client.py -o client.py ; python client.py"

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

print("Join the chatroom by running the following command on the client machine:")
print("Linux clients: ")
print(linux_command.format(ip_address))
print("Windows clients: ")
print(windows_command.format(ip_address))
os.system("python -m http.server 8000 --directory out")