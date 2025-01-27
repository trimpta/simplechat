import threading
import time
import pickle
import socket
import sys
import os


SERVER_IP, SERVER_PORT = 'localhost',5906
TIMEOUT = 60*120

stop_threads = False
nick = None

show_error = True


def clear_screen():
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')

def format_message(sender:str, message: str) -> str:
    """Formats the message to be displayed

    Args:
        sender (str): sender of the message
        message (str): content of the message

    Returns:
        str: formatted message
    """

    return f"{sender} : {message}"

def initiate_connection() -> socket.socket:
    """Initiates a connection with the server

    Returns:
        socket.socket: connection with the server used to recieve messages
    """

    conn_forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    

    try:
        conn_forward.connect((SERVER_IP, SERVER_PORT))
        conn_forward.settimeout(TIMEOUT)

    except Exception as e:
        print("Error trying to connect to server. Contact administrator.")
        disconnect(e)
        # print(f"Error: {e}")

    return conn_forward

def complete_connection() -> socket.socket:
    """Completes the connection with the server

    Returns:
        socket.socket: connection with the server used to recieve messages
    """

    conn_backward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        conn_backward.connect((SERVER_IP, SERVER_PORT + 1))
        conn_backward.settimeout(TIMEOUT)

    except Exception as e:
        print("Error trying to connect to server. Contact administrator.")
        disconnect(e)
        # print(f"Error: {e}")

    return conn_backward

def login(conn: socket.socket) -> bool:
    """Logs in the user to the server

    Args:
        conn (socket.socket): connection with the server

    Returns:
        bool: True if login is successful, False otherwise
    """

    global nick

    for _ in range(3):
        msg = conn.recv(1024).decode()
        
        if msg != "NICK_SEND":
            disconnect(None)
            print("Error while logging in. Please contact administrator.")
        
        nick = input("Enter your nickname: ")
        conn.send(nick.encode())

        response = conn.recv(1024).decode()

        if response == 'NICK_OK':
            print("Login successful.")
            return True

        if response == 'NICK_INVALID':
            print("Nickname is invalid.")

        if response == 'NICK_TAKEN':
            print("Nickname is already taken, try another one.")
            
    return False

def safe_close(conn: socket.socket, message: str = None):
    """Safely closes the connection

    Args:
        conn (socket.socket): connection to be closed
        message (str, optional): Message to be sent before closing the connection. Defaults to None.
    """

    try:
        if message:
            conn.send(message.encode())

        conn.close()
    except:
        pass

def disconnect(error):
    """Disconnects the client from the server"""
    global conn_backward, conn_forward, stop_threads
    stop_threads = True
    
    # if error:
        # print(f"Error: {error}")

    try:
        safe_close(conn_backward, "DISCONNECT")
        safe_close(conn_forward)
    except Exception as e:
        pass
    if stop_threads:
        print("You have been disconnected. Press Enter to close.")
    sys.exit()

def recieve_messages(conn_forward: socket.socket):
    """Recieves messages from the server and outputs them to the console

    Args:
        conn_forward (socket.socket): connection with the server used to recieve messages
    """
    

    while not stop_threads:
        
        try:

            messages = pickle.loads(conn_forward.recv(1024))

            for message in messages:
                
                if len(message) == 1:
                    print(message[0])
                    continue
                
                sender, text = message
                if sender != nick:
                    print(format_message(sender, text))
            
        except Exception as e:
            disconnect(e)

            if not stop_threads:
                print("Error while recieving message. Contact administrator.")
            # print(f"Error: {e}")

def send_messages(conn_backward: socket.socket):
    """Sends messages to the server

    Args:
        conn_backward (socket.socket): connection with the server used to recieve messages
    """

    while not stop_threads:
        
        try:

            message = input()

            if message == "/clear":
                clear_screen()

            if message == "exit":
                conn_backward.send(b'DISCONNECTING')
                disconnect(None)
                break

            conn_backward.send(message.encode())

        except Exception as e:
            disconnect(e)
            if not stop_threads:
                print("Error while sending message. Contact administrator.")
            # print(f"Error: {e}")
        
    return

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


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        disconnect(None)
