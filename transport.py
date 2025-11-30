"""
SHADOW-MESH Transport Layer
Handles TCP-based encrypted message transmission.
"""

import base64
import json
import logging
import socket
import struct
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from crypto_utils import CryptoUtils

logger = logging.getLogger(__name__)


@dataclass
class EncryptedMessage:
    """Represents an encrypted message for transmission."""
    sender: str
    encrypted_content: bytes
    encrypted_key: bytes
    
    def to_bytes(self) -> bytes:
        """Serialize the message for transmission."""
        payload = {
            "sender": self.sender,
            "content": base64.b64encode(self.encrypted_content).decode('utf-8'),
            "key": base64.b64encode(self.encrypted_key).decode('utf-8')
        }
        return json.dumps(payload).encode('utf-8')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedMessage':
        """Deserialize a message from received bytes."""
        payload = json.loads(data.decode('utf-8'))
        return cls(
            sender=payload["sender"],
            encrypted_content=base64.b64decode(payload["content"]),
            encrypted_key=base64.b64decode(payload["key"])
        )


class TransportService:
    """TCP-based encrypted message transport service."""
    
    DEFAULT_PORT = 50001
    BUFFER_SIZE = 65536
    HEADER_SIZE = 4  # 4 bytes for message length
    CONNECTION_TIMEOUT = 10
    
    def __init__(
        self,
        username: str,
        crypto: CryptoUtils,
        port: int = DEFAULT_PORT,
        on_message_received: Optional[Callable[[str, str], None]] = None
    ) -> None:
        """
        Initialize the transport service.
        
        Args:
            username: The local user's display name
            crypto: CryptoUtils instance for encryption/decryption
            port: TCP port to listen on
            on_message_received: Callback(sender, message) when a message arrives
        """
        self.username = username
        self.crypto = crypto
        self.port = port
        self.on_message_received = on_message_received
        
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
    
    def start(self) -> int:
        """
        Start the transport service.
        
        Returns:
            The port the service is listening on
        """
        if self._running:
            return self.port
        
        self._running = True
        
        # Create and bind server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        
        # Try to bind to the specified port, or find an available one
        bound = False
        for port_offset in range(100):
            try:
                # Bind to all interfaces - required for P2P LAN messaging
                # All traffic is encrypted with RSA/Fernet
                self._server_socket.bind(('', self.port + port_offset))
                self.port = self.port + port_offset
                bound = True
                break
            except OSError:
                continue
        
        if not bound:
            raise RuntimeError("Could not find available port for transport service")
        
        self._server_socket.listen(10)
        logger.info(f"Transport service listening on port {self.port}")
        
        # Start server thread
        self._server_thread = threading.Thread(
            target=self._server_loop,
            daemon=True,
            name="TransportServer"
        )
        self._server_thread.start()
        
        return self.port
    
    def stop(self) -> None:
        """Stop the transport service."""
        self._running = False
        
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2)
        
        logger.info("Transport service stopped")
    
    def _server_loop(self) -> None:
        """Accept incoming connections."""
        while self._running:
            try:
                client_socket, addr = self._server_socket.accept()
                logger.debug(f"Connection from {addr}")
                
                # Handle each connection in a separate thread
                handler = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, addr),
                    daemon=True
                )
                handler.start()
                
            except socket.timeout:
                continue
            except socket.error as e:
                if self._running:
                    logger.debug(f"Server socket error: {e}")
            except Exception as e:
                if self._running:
                    logger.error(f"Server loop error: {e}")
    
    def _handle_connection(self, client_socket: socket.socket, addr: tuple) -> None:
        """Handle an incoming connection."""
        try:
            client_socket.settimeout(self.CONNECTION_TIMEOUT)
            
            # Read message length header
            header = self._recv_exact(client_socket, self.HEADER_SIZE)
            if not header:
                return
            
            message_length = struct.unpack('!I', header)[0]
            
            # Validate message length to prevent DoS
            if message_length > 10 * 1024 * 1024:  # 10 MB max
                logger.warning(f"Message too large from {addr}: {message_length}")
                return
            
            # Read message body
            data = self._recv_exact(client_socket, message_length)
            if not data:
                return
            
            # Parse and decrypt message
            try:
                encrypted_msg = EncryptedMessage.from_bytes(data)
                decrypted_text = self.crypto.decrypt_received_message(
                    encrypted_msg.encrypted_content,
                    encrypted_msg.encrypted_key
                )
                
                logger.debug(f"Received message from {encrypted_msg.sender}")
                
                if self.on_message_received:
                    self.on_message_received(encrypted_msg.sender, decrypted_text)
                    
            except Exception as e:
                logger.error(f"Failed to decrypt message from {addr}: {e}")
                
        except socket.timeout:
            logger.debug(f"Connection timeout from {addr}")
        except Exception as e:
            logger.error(f"Error handling connection from {addr}: {e}")
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
    
    def _recv_exact(self, sock: socket.socket, size: int) -> Optional[bytes]:
        """Receive exactly 'size' bytes from socket."""
        data = b''
        while len(data) < size:
            chunk = sock.recv(min(size - len(data), self.BUFFER_SIZE))
            if not chunk:
                return None
            data += chunk
        return data
    
    def send_message(
        self,
        recipient_ip: str,
        recipient_port: int,
        recipient_public_key: str,
        message: str
    ) -> bool:
        """
        Send an encrypted message to a peer.
        
        Args:
            recipient_ip: The recipient's IP address
            recipient_port: The recipient's TCP port
            recipient_public_key: The recipient's public key (PEM, base64 encoded)
            message: The plaintext message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Encrypt the message
            encrypted_content, encrypted_key = self.crypto.encrypt_for_recipient(
                message, recipient_public_key
            )
            
            # Create message object
            encrypted_msg = EncryptedMessage(
                sender=self.username,
                encrypted_content=encrypted_content,
                encrypted_key=encrypted_key
            )
            
            # Serialize
            data = encrypted_msg.to_bytes()
            
            # Connect and send
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.CONNECTION_TIMEOUT)
                sock.connect((recipient_ip, recipient_port))
                
                # Send length header
                header = struct.pack('!I', len(data))
                sock.sendall(header)
                
                # Send message body
                sock.sendall(data)
                
            logger.debug(f"Message sent to {recipient_ip}:{recipient_port}")
            return True
            
        except socket.timeout:
            logger.error(f"Connection timeout to {recipient_ip}:{recipient_port}")
            return False
        except socket.error as e:
            logger.error(f"Socket error sending to {recipient_ip}:{recipient_port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
