# SHADOW-MESH

> Serverless, Encrypted, Peer-to-Peer LAN Chat Application

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

SHADOW-MESH allows users on the same network to discover each other and chat securely without a central server or internet connection.

## Features

- **Zero Configuration**: No server setup required - just run and start chatting
- **Automatic Peer Discovery**: UDP broadcast-based discovery finds peers on your network
- **End-to-End Encryption**: Hybrid RSA/Fernet encryption ensures message security
- **Dark Terminal UI**: IRC-style interface with green-on-black aesthetic
- **Headless Mode**: Run as a CLI application for server deployments

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      SHADOW-MESH                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   GUI       │  │  P2P Engine │  │  Crypto Utils   │  │
│  │  (gui.py)   │◄─┤(p2p_engine) │◄─┤ (crypto_utils)  │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────┘  │
│                          │                               │
│           ┌──────────────┼──────────────┐               │
│           │              │              │               │
│           ▼              ▼              ▼               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Discovery  │  │  Transport  │  │    Cryptography │  │
│  │ (UDP:50000) │  │ (TCP:50001) │  │   (RSA/Fernet)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/Anamitra-Sarkar/shadow_mesh.git
cd shadow_mesh

# Install dependencies
pip install -r requirements.txt
```

## Usage

### GUI Mode (Default)

```bash
# Start with auto-generated username
python main.py

# Start with custom username
python main.py CyberGhost_42
```

### Headless Mode

```bash
# Run without GUI (CLI mode)
python main.py --headless

# With verbose logging
python main.py -v --headless
```

In headless mode, you can use these commands:
- `/peers` - List active peers
- `/msg <username> <message>` - Send a message
- `/help` - Show available commands

## How It Works

### 1. Discovery Layer (`discovery.py`)
- Uses **UDP Broadcast** on Port 50000
- Every 5 seconds, broadcasts: `{"type": "PING", "user": "Ghost_1", "pub_key": "..."}`
- Listens for PINGs and maintains a list of "Active Peers"
- Peers timeout after 15 seconds of inactivity

### 2. Transport Layer (`transport.py`)
When sending a message:
1. Generate a symmetric key (Fernet)
2. Encrypt the message with the symmetric key
3. Encrypt the symmetric key with Recipient's **Public Key** (RSA-OAEP)
4. Send via TCP with length-prefixed framing

### 3. Crypto Utils (`crypto_utils.py`)
- **RSA-2048**: For key exchange (public/private key pairs)
- **Fernet**: For symmetric message encryption
- **OAEP Padding**: SHA-256 for secure key encryption

## File Structure

```
shadow_mesh/
├── main.py           # Entry point
├── p2p_engine.py     # Socket logic coordination
├── crypto_utils.py   # RSA/Fernet cryptography
├── discovery.py      # UDP peer discovery
├── transport.py      # TCP message transport
├── gui.py            # CustomTkinter UI
├── requirements.txt  # Dependencies
└── README.md         # This file
```

## Security Considerations

- **Key Generation**: New RSA keys are generated on each startup
- **Forward Secrecy**: Each message uses a unique Fernet key
- **No Key Storage**: Keys are not persisted to disk
- **Local Network Only**: Traffic stays on your LAN

## Requirements

- Python 3.10+
- `cryptography` >= 42.0.0
- `customtkinter` >= 5.2.0

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**SHADOW-MESH** - Encrypted Peer-to-Peer LAN Communication
