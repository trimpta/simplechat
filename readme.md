# simple chat

A simple, multithreaded chatroom built in Python.

The chatroom uses a **server-client model**:

- **Server**: Manages all connected clients and broadcasts messages.
- **Clients**: Connect to the server, send messages, and receive updates from others in the chatroom.

The server dynamically modifies and serves the `client.py` file to ensure the client script always has the correct server IP.

## Getting Started

### Prerequisites

- Python 3.9 or higher installed on all devices.
- All devices should be on the same local network.

### Steps

1. **Start the Server**:\
   On the server machine, run:

   ```bash
   python serve_client.py
   ```

2. **Connect Clients**:

   - **Windows Clients**:\
     Use the following command:

     ```bash
     curl -s http://<server_ip>:8000/client.py -o client.py && python client.py
     ```

   - **Linux Clients**:\
     Use the following command:

     ```bash
     wget http://<server_ip>:8000/client.py && python3 client.py
     ```

   Replace `<server_ip>` with the IP address of the server machine.

3. **Join the Chatroom**:\
   Enter a nickname when prompted (must be unique among active users), and you're in.

### Example

- Server starts the chatroom:

  ```bash
  python serve_client.py
  ```

- A Windows client connects using:

  ```bash
  curl -s http://192.168.0.101:8000/client.py -o client.py && python client.py
  ```

- A Linux client connects using:

  ```bash
  wget http://192.168.0.101:8000/client.py && python3 client.py
  ```

## Limitations

- **Local Network Only**: This chatroom works only on devices connected to the same local network.
- **No Encryption**: Messages are sent in plain text (so don’t share secrets!).
- **Work in Progress**: Expect a lot of bugs—it’s still under development.
