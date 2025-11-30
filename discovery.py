"""
SHADOW-MESH Discovery Layer
Handles UDP broadcast peer discovery on the local network.
"""

import json
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Peer:
    """Represents a discovered peer on the network."""
    username: str
    ip_address: str
    port: int
    public_key: str
    last_seen: datetime = field(default_factory=datetime.now)
    
    def is_active(self, timeout_seconds: int = 15) -> bool:
        """Check if peer was seen recently."""
        return datetime.now() - self.last_seen < timedelta(seconds=timeout_seconds)


class DiscoveryService:
    """UDP broadcast-based peer discovery service."""
    
    DISCOVERY_PORT = 50000
    BROADCAST_INTERVAL = 5  # seconds
    PEER_TIMEOUT = 15  # seconds
    BUFFER_SIZE = 4096
    
    def __init__(
        self,
        username: str,
        public_key: str,
        tcp_port: int,
        on_peer_discovered: Optional[Callable[[Peer], None]] = None,
        on_peer_lost: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Initialize the discovery service.
        
        Args:
            username: The local user's display name
            public_key: The local user's public key (PEM, base64 encoded)
            tcp_port: The TCP port for direct messaging
            on_peer_discovered: Callback when a new peer is found
            on_peer_lost: Callback when a peer goes offline
        """
        self.username = username
        self.public_key = public_key
        self.tcp_port = tcp_port
        self.on_peer_discovered = on_peer_discovered
        self.on_peer_lost = on_peer_lost
        
        self._peers: Dict[str, Peer] = {}
        self._peers_lock = threading.Lock()
        
        self._running = False
        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        
        self._broadcast_socket: Optional[socket.socket] = None
        self._listen_socket: Optional[socket.socket] = None
        self._local_ip = self._get_local_ip()
    
    @staticmethod
    def _get_local_ip() -> str:
        """Get the local IP address."""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # This doesn't actually connect - just determines the interface
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
            except Exception:
                ip = '127.0.0.1'
            finally:
                s.close()
            return ip
        except Exception:
            return '127.0.0.1'
    
    def get_peers(self) -> Dict[str, Peer]:
        """Get a copy of the current peer list."""
        with self._peers_lock:
            return dict(self._peers)
    
    def get_peer(self, username: str) -> Optional[Peer]:
        """Get a specific peer by username."""
        with self._peers_lock:
            return self._peers.get(username)
    
    def start(self) -> None:
        """Start the discovery service."""
        if self._running:
            return
        
        self._running = True
        logger.info(f"Starting discovery service as {self.username} on {self._local_ip}")
        
        # Start broadcast thread
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            daemon=True,
            name="DiscoveryBroadcast"
        )
        self._broadcast_thread.start()
        
        # Start listen thread
        self._listen_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="DiscoveryListen"
        )
        self._listen_thread.start()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="DiscoveryCleanup"
        )
        self._cleanup_thread.start()
    
    def stop(self) -> None:
        """Stop the discovery service."""
        self._running = False
        
        # Close sockets to unblock threads
        if self._broadcast_socket:
            try:
                self._broadcast_socket.close()
            except Exception:
                pass
        
        if self._listen_socket:
            try:
                self._listen_socket.close()
            except Exception:
                pass
        
        # Wait for threads to finish
        for thread in [self._broadcast_thread, self._listen_thread, self._cleanup_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2)
        
        logger.info("Discovery service stopped")
    
    def _create_ping_message(self) -> bytes:
        """Create a PING broadcast message."""
        message = {
            "type": "PING",
            "user": self.username,
            "pub_key": self.public_key,
            "tcp_port": self.tcp_port
        }
        return json.dumps(message).encode('utf-8')
    
    def _broadcast_loop(self) -> None:
        """Continuously broadcast our presence."""
        try:
            self._broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._broadcast_socket.settimeout(1.0)
            
            while self._running:
                try:
                    message = self._create_ping_message()
                    self._broadcast_socket.sendto(
                        message,
                        ('<broadcast>', self.DISCOVERY_PORT)
                    )
                    logger.debug(f"Broadcast PING sent")
                except socket.error as e:
                    if self._running:
                        logger.warning(f"Broadcast error: {e}")
                
                # Sleep in small increments to allow quick shutdown
                for _ in range(self.BROADCAST_INTERVAL * 10):
                    if not self._running:
                        break
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Broadcast thread error: {e}")
        finally:
            if self._broadcast_socket:
                try:
                    self._broadcast_socket.close()
                except Exception:
                    pass
    
    def _listen_loop(self) -> None:
        """Listen for broadcast messages from other peers."""
        try:
            self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._listen_socket.settimeout(1.0)
            
            try:
                # Bind to all interfaces - required for P2P LAN discovery
                # All traffic is encrypted, so this is safe
                self._listen_socket.bind(('', self.DISCOVERY_PORT))
            except OSError as e:
                logger.error(f"Failed to bind discovery port: {e}")
                return
            
            logger.info(f"Listening for peers on port {self.DISCOVERY_PORT}")
            
            while self._running:
                try:
                    data, addr = self._listen_socket.recvfrom(self.BUFFER_SIZE)
                    self._handle_discovery_message(data, addr)
                except socket.timeout:
                    continue
                except socket.error as e:
                    if self._running:
                        logger.debug(f"Listen error: {e}")
        except Exception as e:
            logger.error(f"Listen thread error: {e}")
        finally:
            if self._listen_socket:
                try:
                    self._listen_socket.close()
                except Exception:
                    pass
    
    def _handle_discovery_message(self, data: bytes, addr: tuple) -> None:
        """Process a received discovery message."""
        try:
            message = json.loads(data.decode('utf-8'))
            
            if message.get("type") != "PING":
                return
            
            username = message.get("user")
            public_key = message.get("pub_key")
            tcp_port = message.get("tcp_port", 50001)
            sender_ip = addr[0]
            
            # Ignore our own broadcasts
            if username == self.username:
                return
            
            if not username or not public_key:
                return
            
            # Update or add peer
            with self._peers_lock:
                is_new = username not in self._peers
                
                self._peers[username] = Peer(
                    username=username,
                    ip_address=sender_ip,
                    port=tcp_port,
                    public_key=public_key,
                    last_seen=datetime.now()
                )
                
                if is_new:
                    logger.info(f"Discovered new peer: {username} at {sender_ip}")
                    if self.on_peer_discovered:
                        # Call callback outside of lock
                        peer = self._peers[username]
            
            if is_new and self.on_peer_discovered:
                self.on_peer_discovered(peer)
                
        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON from {addr}")
        except Exception as e:
            logger.debug(f"Error handling discovery message: {e}")
    
    def _cleanup_loop(self) -> None:
        """Periodically remove stale peers."""
        while self._running:
            try:
                lost_peers = []
                
                with self._peers_lock:
                    stale = [
                        username for username, peer in self._peers.items()
                        if not peer.is_active(self.PEER_TIMEOUT)
                    ]
                    for username in stale:
                        del self._peers[username]
                        lost_peers.append(username)
                        logger.info(f"Peer timed out: {username}")
                
                # Call callbacks outside of lock
                if self.on_peer_lost:
                    for username in lost_peers:
                        self.on_peer_lost(username)
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            
            # Sleep in small increments
            for _ in range(50):
                if not self._running:
                    break
                time.sleep(0.1)
