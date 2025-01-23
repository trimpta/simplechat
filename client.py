import threading
import pickle
import socket
import argparse
import re

SERVER_IP, SERVER_PORT = 'localhost',5906


def initiate_connection():
    conn_forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    

    try:
        conn_forward.connect((SERVER_IP, SERVER_PORT))
        conn_forward.settimeout(50)
        print("Established connection with server.")

    except Exception as e:
        print("Error trying to connect to server. Contact administrator.")
        print(f"Error: {e}")


    return conn_forward

def complete_connection():
    conn_backward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        conn_backward.connect((SERVER_IP, SERVER_PORT + 1))
        conn_backward.settimeout(50)
        print("Established reverse connection with server.")

    except Exception as e:
        print("Error trying to connect to server. Contact administrator.")
        print(f"Error: {e}")

    return conn_backward

def login(conn: socket.socket):

    while True:
        msg = conn.recv(1024).decode()
        print(f"Logging in: {msg}")
        if msg != "NICK_SEND":
            raise(ValueError(msg))
        
        nick = input("Enter your nickname: ")
        conn.send(nick.encode())

        response = conn.recv(1024).decode()

        if response == 'NICK_OK':
            return True

        if response == 'NICK_INVALID':
            print("Nickname is invalid.")

        if response == 'NICK_TAKEN':
            print("Nickname is already taken, try another one.")
            
    return False

def disconnect(conn_forward: socket.socket, conn_backward: socket.socket):
    conn_backward.close()
    conn_forward.close()


def recieve_messages(conn_forward: socket.socket):

    while True:
        
        try:

            messages = pickle.loads(conn_forward.recv(1024))
            for message in messages:
                print(message)

        except Exception as e:
            print("Error while recieving message. Contact administrator.")
            print(f"Error: {e}")
            disconnect()

def send_messages(conn_backward: socket.socket):

    while True:
        
        try:

            message = input(">>>")
            conn_backward.send(message.encode())

        except Exception as e:
            print("Error while sending message. Contact administrator.")
            print(f"Error: {e}")
            disconnect()


def main():

    conn_forward  = initiate_connection()
    
    if not login(conn_forward):
        print("Login Failed, Please try again.")
        return
    
    conn_backward = complete_connection()

    recv = threading.Thread(target = recieve_messages, args = (conn_forward,))
    send = threading.Thread(target = send_messages, args = (conn_backward,))

    recv.start()
    send.start()


main()
    
