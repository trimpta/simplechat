import threading
import pickle
import socket
import argparse
import re

SERVER_IP, SERVER_PORT = 'localhost',5906

def connect():
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conn.connect((SERVER_IP, SERVER_PORT))
        conn.settimeout(50)

    except Exception as e:
        print("Error trying to connect to server. Contact administrator.")
        print(f"Error: {e}")

    return conn


def login(conn: socket.socket):

    while True:
        msg = conn.recv(512).decode()
        
        if msg != "NICK_SEND":
            raise(ValueError)
        
        nick = input("Enter your nickname: ")
        conn.send(nick.encode())

        response = conn.recv(512).decode()

        if response == 'NICK_OK':
            break

        if response == 'NICK_INVALID':
            print("Nickname is invalid.")

        if response == 'NICK_TAKEN':
            print("Nickname is already taken, try another one.")
            
        
    return True


conn = connect()
login(conn)
    