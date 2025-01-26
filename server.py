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
admins = []

commands = {
    '/exit': 'Disconnect from chat',
    '/list': 'List all connected members',
    '/help': 'List all commands',
    '/kick': 'Kick a user from the chat',
}

commands_server = {
    '/exit': 'Disconnect from chat',
    '/list': 'List all connected members',
    '/kick': 'Kick a user from the chat',
    '/say': 'Send a message to all users',
    '/tellraw': 'send a raw message',
    '/admin': 'Add a user to the admin list',
    '/deop': 'Remove a user from the admin list',
    '/list_admins': 'List all admins',
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
    
    if nickname in clients:
        clients[nickname][0].close()
        clients[nickname][1].close()
        
        try:
            clients.pop(nickname)
        except KeyError:
            pass

def commands_hander():
    """Handles commands recieved from clients"""

    global commands_queue
    
    while True:
        
        if not commands_queue:
            continue

        with threading.Lock():
            popped_commands = commands_queue
            commands_queue = []

        print('\n'.join([f"{sender} :{command}" for sender, command in popped_commands]))

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
                    ("SERVER:\n ", ''.join([f"{command} : {commands[command]}\n" for command in commands])),
                ]                
                clients[sender][0].send(pickle.dumps(msg))

            elif command.startswith('/kick'):

                if sender in admins:
                    nickname = command.split()[1]
                    if nickname in clients:
                        disconnect(nickname)
                    else:
                        clients[sender][0].send(pickle.dumps([("SERVER", "Client not found")]))
                else:
                    clients[sender][0].send(pickle.dumps([("SERVER", "You are not an admin")]))
        


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

    return message.split()[0] in commands



def client_handler(conn_forward: socket.socket, addr:str, nickname: str):
    """Handles messages recieved from clients

    Args:
        conn_forward (socket.socket): connection to the client used to send messages from server to client
        addr (str): address of the client
        nickname (str): nickname of the client
    """

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
                commands_queue.append((nickname, message))
                continue
            
            message_queue.append((nickname, message))

    except ConnectionAbortedError as e:
        print(f"CLIENTERROR: {nickname}@{addr} disconnected")
        disconnect(nickname)

    message_queue.append(("SERVER", f"{nickname} LEFT THE CHAT!"))

    


def broadcast_messages():
    """Broadcasts messages to all clients and prints them to the server"""

    global message_queue
    
    while True:
        
        if not message_queue:
            continue

        with threading.Lock():
            popped_messages = message_queue
            message_queue = []

        # print('\n'.join([f"{sender} : {message}" for sender, message in popped_messages]))

        for msg in popped_messages:
            
            if len(msg) != 2:
                continue
            
            sender, message = msg
            print(f"{sender} : {message}")
                
        
        for client in clients:
            
            try:
                clients[client][0].send(pickle.dumps(popped_messages))
            
            except ConnectionResetError as e:
                print(f"CLIENTERROR: Error sending message to {client}@{clients[client][2]}")
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

def server_commands():
    """Handles commands recieved from the server"""

    while True:

        try:
            command = input().split()

            if command[0] not in commands_server:
                print(f"SERVERERROR: Invalid command")
                continue

            if command[0] == '/exit':
                for client in clients:
                    disconnect(client)
                break

            elif command[0] == '/list':
                print(''.join([f"{client} : {clients[client][2]}\n" for client in clients]))

            elif command[0] == '/kick':
                if command[1] in clients:
                    disconnect(command[1])
                else:
                    print("Client not found")

            elif command[0] == '/say':
                #Unicode blank character is used so client.py doesnt filter out the message
                message_queue.append(("SERVER", ' '.join(command[2:])))

            elif command[0] == '/tellraw':
                message_queue.append((
                    ' '.join(command[1:]
                             ),))
                
            elif command[0] == '/admin':
                if command[1] not in admins and command[1] in clients:
                    admins.append(command[1])
            
            elif command[0] == '/deop':
                if command[1] in admins:
                    admins.remove(command[1])
                else:
                    print("User not an admin")

            elif command[0] == '/list_admins':
                print(''.join([f"{admin}\n" for admin in admins]))
            
            elif command[0] == '/help':
                print(''.join([f"{command} : {commands_server[command]}\n" for command in commands_server]))


        except Exception as e:
            print(f"SERVERERROR: Error while processing command")
            print(f"SERVERERROR: {e}")
        

        

def main():
    broadcast_thread = threading.Thread(target = broadcast_messages)
    broadcast_thread.start()

    commands_thread = threading.Thread(target = commands_hander)
    commands_thread.start()

    connections_thread = threading.Thread(target = accept_connections)
    connections_thread.start()

    server_commands_thread = threading.Thread(target = server_commands)
    server_commands_thread.start()


if __name__ == '__main__':
    main()