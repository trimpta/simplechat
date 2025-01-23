import threading
import pickle
import socket
import argparse

SERVER_IP, SERVER_PORT = 'localhost',5906

conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    conn.connect((SERVER_IP, SERVER_PORT))
    conn.settimeout(50)

except Exception as e:
    print("Error trying to connect to server. Contact administrator.")
    print(f"Error: {e}")


