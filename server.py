import threading
import pickle
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

done = False

commands = {
    '/exit': 'Disconnect from chat',
    '/list': 'List all connected members',
    '/help': 'Show description for all commands, or /help <cmd> for a specific command.',
    '/kick': 'Kick a user from the chat. Requires admin previlages. /kick <nickname>',
    '/whisper': 'Send a private message to a user. /whisper <target username> message',
    '/clear' : 'Clear your screen. [WARNING] All messages will be gone, and you wont be able to see them again'
}

commands_server = {
    'exit': 'Disconnect from chat',
    'list': 'List all connected members',
    'kick': 'Kick a user from the chat',
    'say': 'Send a message to all users',
    'tellraw' : 'send a raw message',
    'whisper' : 'send a message to a specific user',
    'rawsp' : 'send a raw message to a specific user',
    'admin': 'Add a user to the admin list',
    'deop': 'Remove a user from the admin list',
    'list_admins': 'List all admins',
    'help': 'List all commands'
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

def whisper(target: str, message: str):
    """send raw message to specific target

    Args:
        target (str): nickname of target
        message (str): message.
    """
    clients[target][0].send(pickle.dumps([(message, )]))

def commands_hander():
    """Handles commands recieved from clients"""

    global commands_queue, done
    
    while not done:
        
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

                str = ''.join([f"{'[ADMIN] ' if client in admins else ''}{client}, " for client in clients])                
                whisper( sender, str)
                
            elif command == '/help':
                msg =  ''.join([f"{command} : {commands[command]}\n" for command in commands])           
                whisper(sender, msg)

            elif command.startswith('/kick'):

                if sender in admins:
                    nickname = command.split()[1]
                    if nickname in clients:
                        disconnect(nickname)
                    else:
                        clients[sender][0].send(pickle.dumps([("SERVER", "Client not found")]))
                else:
                    clients[sender][0].send(pickle.dumps([("SERVER", "You are not an admin")]))

            elif command.startswith('/help') and len(command.split()) == 2:

                _, cmd = command.split()

                if cmd in commands:
                    whisper(sender, f"{cmd} : {commands[cmd]}")

                if f"/{cmd}" in commands:
                    whisper(sender, f"/{cmd} : {commands[f'/{cmd}']}")

            
            elif command.startswith('/whisper'):

                    split = command.split()
                    # split = ['/whisper', 'target_nick', 'msgword1', 'msgword2', ....]

                    print(f"{sender} : {command}")
                    if len(split) == 1:
                        # clients[sender][0].send(pickle.dumps([("SERVER", "Please specify user to send message to.")]))
                        whisper(sender, "Please specify user to send message to")
                        continue

                    if len(split) == 2:
                        # clients[sender][0].send(pickle.dumps([("SERVER", "Please enter message content.")]))
                        whisper(sender, "Please enter message content.")
                        continue

                    target = command.split()[1]

                    if target not in clients:
                        clients[sender][0].send(pickle.dumps([("SERVER", "Client not found")]))
                        continue

                    msg = f"[WHISPER] {sender} : " + ' '.join(command.split()[2:])
                    whisper(target, msg)
                    # clients[target][0].send(pickle.dumps([(f"[WHISPER] {sender} : {msg}", )]))

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

    global done

    print(f"New connection from {nickname}@{addr}")

    try:
        while not done:

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

    global message_queue, done
    
    while not done:
        
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
    
    global done

    while not done:
        #conn_forward is used to send messages to client, and conn_backward is used to recieve messages from client
        #conn_forward is also used to recieve from client until a proper connection is established

        conn_forward,addr = server_conn.accept()

        try:
            nickname = get_username(conn_forward)
        
        except ConnectionAbortedError:
            print(f"CLIENTERROR: @{addr} aborted during login.")
            continue
        
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

        whisper(nickname, 'Welcome to the chatroom, all messages you send are public by default. do /help to get a list of commands.')
        message_queue.append(("SERVER", JOIN_MSG.format(nickname)))

    
        client_thread = threading.Thread(target = client_handler, args = (conn_backward, addr, nickname))
        client_thread.start()

def server_commands():
    """Handles commands recieved from the server"""

    global done

    while not done:

        try:
            command = input().split()

            if command[0] not in commands_server:
                print(f"SERVERERROR: Invalid command")
                continue

            if command[0] == 'exit':
                
                for client in clients:
                    disconnect(client)

                done = True
                break

            elif command[0] == 'list':
                print(''.join([f"{'[ADMIN] ' if client in admins else ''}{client} : {clients[client][2]}\n" for client in clients]))

            elif command[0] == 'kick':
                if command[1] in clients:
                    disconnect(command[1])
                else:
                    print("Client not found")

            elif command[0] == 'say':
                #Unicode blank character is used so client.py doesnt filter out the message
                message_queue.append(("SERVER", ' '.join(command[2:])))

            elif command[0] == 'tellraw':
                message_queue.append((' '.join(command[1:]),))

            elif command[0] in ['whisper', 'rawsp']:

                if len(command) == 1:
                    # clients[sender][0].send(pickle.dumps([("SERVER", "Please specify user to send message to.")]))
                    print("Please specify user to send message to")
                    continue

                if len(command) == 2:
                    # clients[sender][0].send(pickle.dumps([("SERVER", "Please enter message content.")]))
                    print("Please enter message content.")
                    continue

                target = command[1]

                if target not in clients:
                    print("Target not found.")
                    continue

                msg = ('' if command[0] == 'rawsp' else "[WHISPER] SERVER : ") + ' '.join(command[2:]) 
                whisper(target, msg)
                
            elif command[0] == 'admin':
                if command[1] not in admins and command[1] in clients:
                    admins.append(command[1])
                    print(f"Added {command[1]} to admins list.")
            
            elif command[0] == 'deop':
                if command[1] in admins:
                    admins.remove(command[1])
                else:
                    print("User not an admin")

            elif command[0] == 'list_admins':
                print(''.join([f"{admin}\n" for admin in admins]))
            
            elif command[0] == 'help':
                print(''.join([f"{command} : {commands_server[command]}\n" for command in commands_server]))

        except EOFError as e:
            print("Recieved keyboard interrupt, exiting")
            done = True
            break
        
        except KeyboardInterrupt as e:

            print("Recieved keyboard interrupt, exiting")
            done = True
            break
        
        # except Exception as e:
        #     print(f"SERVERERROR: Error while processing command")
        #     print(f"SERVERERROR: {e}")

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