import threading
import pickle
import http.server
import socketserver
import socket
import re

HOST, PORT, WEB_PORT = '0.0.0.0', 5906, 8000
VALID_USERNAME = re.compile(r"^[A-Za-z0-9\-_\.]{3,20}$")
TIMEOUT = 60*120

JOIN_MSG = "{} JOINED THE CHAT!"

clients:dict[str, list[socket.socket,list[tuple]], list[socket.socket,list[tuple]]] = {}  # {nick : [forward_connection/0, backward_connection/1, (address, port)/2]}
commands_queue = []
message_queue = []
commands = ['/exit', '/list', '/help']
commands_description = {
    '/exit': 'Disconnect from chat',
    '/list': 'List all connected members',
    '/help': 'List all commands'
}


#initialize sockets for server and reciever
server_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_conn.bind((HOST, PORT))
server_conn.settimeout(TIMEOUT)
server_conn.listen()

recv_conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
recv_conn.bind((HOST, PORT + 1))
recv_conn.settimeout(500)
recv_conn.listen()


def disconnect(nickname: str):
    """Disconnects a user from the chat

    Args:
        nickname (str): The nickname of the user to be disconnected
    """
    
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
    """Handles commands recieved from clients"""

    global commands_queue
    
    while True:
        
        if not commands_queue:
            continue

        with threading.Lock():
            popped_commands = commands_queue
            commands_queue = []

        print('\n'.join([f"{sender} :/{command}" for sender, command in popped_commands]))

        for sender, command in popped_commands:
            
            if command == '/exit':
                disconnect(sender)
            elif command == '/list':
                msg =  [
                    ("CONNECTED MEMBERS: ", ','.join(clients.keys())),
                ]
                clients[sender][0].send(pickle.dumps(msg))
            elif command == '/help':
                msg =  [
                    ("SERVER: ", ''.join([f"\t{command} : {commands_description[command]}\n" for command in commands])),
                ]                
                clients[sender][0].send(pickle.dumps(msg))
        


def get_username(conn_forward: socket.socket) -> str:
    """Gets the username of the client

    Args:
        conn_forward (socket.socket): The socket connection to the client

    Raises:
        ValueError: If the username is invalid

    Returns:
        str: The username of the client
    """
    
    for _ in range(3):
        conn_forward.send(b'NICK_SEND')
        nickname:str = conn_forward.recv(256).decode()

        if re.fullmatch(VALID_USERNAME, nickname) is None or nickname == "SERVER":
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
    """Checks if a message is valid

    Args:
        message (str): The message to be checked

    Returns:
        bool: True if the message is valid, False otherwise
    """

    return True

def is_command(message: str) -> bool:
    """Checks if a message is a command

    Args:
        message (str): The message to be checked

    Returns:
        bool: True if the message is a command, False otherwise
    """

    return message in commands



def client_handler(conn_forward: socket.socket, addr:str, nickname: str):
    """Handles messages recieved from clients

    Args:
        conn_forward (socket.socket): connection to the client used to send messages from server to client
        addr (str): address of the client
        nickname (str): nickname of the client

    Raises:
        ValueError: If an empty message is recieved
    """

    print(f"New connection from {nickname}@{addr}")

    try:
        while True:

            message = conn_forward.recv(1024).decode()

            if not message:
                disconnect(nickname)
                raise ValueError("Empty message recieved")

            if message == "DISCONNECT":
                disconnect(nickname)
                break

            if not is_valid_message(message):
                continue

            if is_command(message):
                commands_queue.append((nickname, message))
                continue
            
            message_queue.append((nickname, message))

    except Exception as e:
        print(f"CLIENTERROR: Error recieving message from {nickname}@{addr}")
        print(f"CLIENTERROR: {e}")
        disconnect(nickname)

    


def broadcast_messages():
    """Broadcasts messages to all clients and prints them to the server"""

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
    """Accepts connections from clients and creates a new thread to handle each client connection"""
    
    while True:
        #conn_forward is used to send messages to client, and conn_backward is used to recieve messages from client
        #conn_forward is also used to recieve from client until a proper connection is established

        conn_forward,addr = server_conn.accept()

        try:
            nickname = get_username(conn_forward)
        
        except ValueError as e:
            print(f"CLIENTERROR: Invalid username from @{addr}")
            print(f"CLIENTERROR: {e}\nCLIENTERROR")
            conn_forward.close()
            continue

        try:
            conn_backward, addr = recv_conn.accept()
        except Exception as e:
            print(f"CLIENTERROR: Error getting back connection from {nickname}@{addr}")
            print(f"CLIENTERROR: {e}\nCLIENTERROR")
        
        
        clients[nickname] = [conn_forward, conn_backward, addr]
        message_queue.append(("SERVER", JOIN_MSG.format(nickname)))

    
        client_thread = threading.Thread(target = client_handler, args = (conn_backward, addr, nickname))
        client_thread.start()

def main():
    broadcast_thread = threading.Thread(target = broadcast_messages)
    broadcast_thread.start()

    commands_thread = threading.Thread(target = commands_hander)
    commands_thread.start()

    accept_connections()


if __name__ == '__main__':
    main()