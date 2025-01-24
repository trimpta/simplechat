import socket
import http.server

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

print(f"IP Address: {ip_address}")

with open("client.py", "r") as f:
    content = f.read()
    content = content.replace("localhost", ip_address)
    
with open("out/client.py", "w") as f:
    f.write(content)

