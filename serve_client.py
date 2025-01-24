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
server_conn.settimeout(60*10)
server_conn.listen()

recv_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
recv_conn.bind((HOST, PORT + 1))
recv_conn.settimeout(500)
recv_conn.listen()


def disconnect(nickname: str):
    
    clients[nickname][0].close()
    clients[nickname][1].close()

    message_queue.append(("SERVER", f"{nickname} LEFT THE CHAT!"))
    clients.pop(nickname)

def web_handler():
    hander = http.server.SimpleHTTPRequestHandler(directory="out")
    with socketserver.TCPServer("", WEB_PORT, hander) as httpd:
        print("serving at port", WEB_PORT)
        httpd.serve_forever()

def commands_hander():
    raise NotImplementedError

def get_username(conn_forward: socket.socket) -> str:
    
    for _ in range(3):
        conn_forward.send(b'NICK_SEND')
        nickname:str = conn_forward.recv(256).decode()

        if re.fullmatch(VALID_USERNAME, nickname) is None:
            conn_forward.send(b'NICK_INVALID')
            continue

        if nickname in clients:
            conn_forward.send(b'NICK_TAKEN')
            continue

        conn_forward.send(b'NICK_OK')
        break
    else:
        raise ValueError
    
    
    return nickname

def is_valid_message(message: str) -> bool:
    return True

def is_command(message: str) -> bool:
    return False

# def broadcast_to_all(message:str):
#     for client in clients:
#         clients[client][1].send(message.encode())



def client_handler(conn_forward: socket.socket, addr:str, nickname: str):

    print(f"New connection from {nickname}@{addr}")

    try:
        while True:

            message = conn_forward.recv(1024).decode()

            if not message:
                disconnect(nickname)
                break
            
            if message == "DISCONNECT":
                disconnect(nickname)
                break

            if not is_valid_message(message):
                continue

            if is_command(message):
                commands_queue.append(message)
                continue
            
            message_queue.append((nickname, message))

    except Exception as e:
        print(f"CLIENTERROR: Error recieving message from {nickname}@{addr}")
        print(f"CLIENTERROR: {e}")
        disconnect(nickname)

    


def broadcast_messages():
    global message_queue
    
    while True:
        
        if not message_queue:
            continue

        with threading.Lock():
            popped_messages = message_queue
            message_queue = []

        print('\n'.join([f"{sender} : {message}" for sender, message in popped_messages]))
        
        for client in clients:
            
            try:
                clients[client][0].send(pickle.dumps(popped_messages))
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
            conn_backward, addr = recv_conn.accept()
        except Exception as e:
            print(f"CLIENTERROR: Error getting back connection from {nickname}@{addr}")
            print(f"CLIENTERROR: {e}")
        
        clients[nickname] = [conn_forward, conn_backward, addr]
        message_queue.append(("SERVER", JOIN_MSG.format(nickname)))

    
        client_thread = threading.Thread(target = client_handler, args = (conn_backward, addr, nickname))
        client_thread.start()

def main():

    broadcast_thread = threading.Thread(target = broadcast_messages)
    broadcast_thread.start()

    accept_connections()


if __name__ == '__main__':
    main()