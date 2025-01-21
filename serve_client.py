import asyncio
import threading
import pickle
import http.server
import socketserver
import socket
import re

HOST, PORT, WEB_PORT = '0.0.0.0', 82382, 8000
VALID_USERNAME = re.compile(r"^[A-Za-z0-9\-_\.]{3,20}$")



def web_hander():
    hander = http.server.SimpleHTTPRequestHandler(directory="out")
    with socketserver.TCPServer(("", WEB_PORT), hander) as httpd:
        print("serving at port", WEB_PORT)
        httpd.serve_forever()

def commands_hander():
    raise NotImplementedError

def get_username(conn: socket.socket) -> str:
    
    for _ in range(3):
        conn.send(b'NICK_SEND')
        nickname:str = conn.recv(256).decode()

        if re.fullmatch(VALID_USERNAME, nickname) is None:
            conn.send(b'NICK_INVALID')

        if nickname in clients:
            conn.send(b'NICK_TAKEN')

        break
    else:
        raise ValueError
    
    return nickname

def message_validator(message: str) -> bool:
    return True

def is_command(message: str) -> bool:
    return True

def broadcast_to_all(message:str):
    for client in clients:
        clients[client][1].send(message.encode())


def format_message(sender:str, message: str):
    return f"{sender} : {message}"



def client_handler(conn: socket.socket, addr:str):

    try:
        nickname = get_username(conn)
    
    except ValueError as e:
        print(f"CLIENTERROR: Error trying to get username from {addr}")
        conn.close()

    clients[nickname] = [conn, addr]

    try:
        while True:
            message = conn.recv(512).decode()
            
            if not message_validator(nickname, message):
                continue

            if is_command(message):
                commands_queue.append(message)
                continue
            
            messages_queue.append(format_message(nickname, message))

    except Exception as e:
        print(f"CLIENTERROR: Error recieving message from {nickname}@{addr}")


def broadcast_messages():
    while True:
        
        if not message_queue:
            continue

        popped_messages, message_queue = message_queue, []
        
        for client in clients:
            
            try:
                clients[client][0].send(pickle.dumps(popped_messages))
            except Exception as e:
                print(e)
                #Disconnect client
    


clients:dict[str, list[socket.socket,list[tuple]]] = {}  # {nick : [connection/0, (address, port)/1]}
commands_queue = []
messages_queue = []