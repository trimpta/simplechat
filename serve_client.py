import threading
import pickle
import http.server
import socketserver
import socket
import re

HOST, PORT, WEB_PORT = '0.0.0.0', 5906, 8000
VALID_USERNAME = re.compile(r"^[A-Za-z0-9\-_\.]{3,20}$")


JOIN_MSG = "{} JOINED THE CHAT!"


clients:dict[str, list[socket.socket,list[tuple]], list[socket.socket,list[tuple]]] = {}  # {nick : [forward_connection/0, backward_connection/1, (address, port)/2]}
commands_queue = []
message_queue = []


server_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_conn.bind((HOST, PORT))
server_conn.settimeout(500)
server_conn.listen()

recv_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
recv_conn.bind((HOST, PORT + 1))
recv_conn.settimeout(500)
recv_conn.listen()


def disconnect(nickname: str):
    
    clients[nickname][0].close()
    clients[nickname][1].close()

    clients.pop(nickname)

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
    
    conn.send(b'NICK_OK')
    
    return nickname

def message_validator(message: str) -> bool:
    return True

def is_command(message: str) -> bool:
    return False

# def broadcast_to_all(message:str):
#     for client in clients:
#         clients[client][1].send(message.encode())


def format_message(sender:str, message: str):
    return f"{sender} : {message}"


def client_handler(conn_forward: socket.socket, addr:str, nickname: str):



    try:
        while True:
            message = conn_forward.recv(1024).decode()
            
            if not message_validator(nickname, message):
                continue

            if is_command(message):
                commands_queue.append(message)
                continue
            
            message_queue.append(format_message(nickname, message))

    except Exception as e:
        print(f"CLIENTERROR: Error recieving message from {nickname}@{addr}")
        print(f"CLIENTERROR: {e}")
        disconnect(nickname)

    


def broadcast_messages():
    global message_queue
    
    while True:
        
        if not message_queue:
            continue

        popped_messages, message_queue = message_queue, []
        print('\n'.join(popped_messages))
        
        for client in clients:
            
            try:
                clients[client][1].send(pickle.dumps(popped_messages))
            except Exception as e:
                print(f"CLIENTERROR: Error sending message to {client}@{clients[client][2]}")
                print(e)
                disconnect(client)

def accept_connections():
    while True:
        conn_forward,addr = server_conn.accept()

        try:
            nickname = get_username(conn_forward)

        
        except ValueError as e:
            print(f"CLIENTERROR: Invalid username from @{addr}")
            print(f"CLIENTERROR: {e}")
            conn_forward.close()
            continue

        try:
            conn_backward, addr = server_conn.accept()
        except Exception as e:
            print(f"CLIENTERROR: Error getting back connection from {nickname}@{addr}")
            print(f"CLIENTERROR: {e}")
        

        clients[nickname] = [conn_forward, conn_backward, addr]
        message_queue.append(JOIN_MSG.format(nickname))

    
        client_thread = threading.Thread(target = client_handler, args = (conn_forward, addr, nickname))
        client_thread.start()

def main():

    broadcast_thread = threading.Thread(target = broadcast_messages)
    broadcast_thread.start()

    accept_connections()



main()