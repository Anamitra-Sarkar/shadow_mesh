"""
SHADOW-MESH P2P Engine
Main coordination layer for peer discovery and encrypted messaging.
"""

import logging
import random
import string
import threading
from typing import Callable, Dict, List, Optional

from crypto_utils import CryptoUtils
from discovery import DiscoveryService, Peer
from transport import TransportService

logger = logging.getLogger(__name__)


class P2PEngine:
    """
    Core P2P engine that coordinates discovery and transport services.
    
    This is the main interface for the SHADOW-MESH application.
    """
    
    def __init__(
        self,
        username: Optional[str] = None,
        on_peer_discovered: Optional[Callable[[Peer], None]] = None,
        on_peer_lost: Optional[Callable[[str], None]] = None,
        on_message_received: Optional[Callable[[str, str], None]] = None
    ) -> None:
        """
        Initialize the P2P engine.
        
        Args:
            username: Display name (auto-generated if not provided)
            on_peer_discovered: Callback when a new peer is found
            on_peer_lost: Callback when a peer goes offline
            on_message_received: Callback(sender, message) when a message arrives
        """
        self.username = username or self._generate_username()
        self._on_peer_discovered = on_peer_discovered
        self._on_peer_lost = on_peer_lost
        self._on_message_received = on_message_received
        
        # Initialize cryptographic utilities
        self.crypto = CryptoUtils()
        
        # Services will be initialized on start
        self._transport: Optional[TransportService] = None
        self._discovery: Optional[DiscoveryService] = None
        
        self._running = False
        self._lock = threading.Lock()
        
        logger.info(f"P2P Engine initialized for user: {self.username}")
    
    @staticmethod
    def _generate_username() -> str:
        """Generate a random anonymous username."""
        adjectives = [
            "Ghost", "Shadow", "Phantom", "Cyber", "Dark", 
            "Silent", "Hidden", "Stealth", "Crypto", "Anon"
        ]
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{random.choice(adjectives)}_{suffix}"
    
    @property
    def public_key(self) -> str:
        """Get the local user's public key."""
        return self.crypto.get_public_key_pem()
    
    @property
    def tcp_port(self) -> int:
        """Get the TCP port for direct messaging."""
        if self._transport:
            return self._transport.port
        return TransportService.DEFAULT_PORT
    
    def start(self) -> None:
        """Start all P2P services."""
        with self._lock:
            if self._running:
                return
            
            logger.info("Starting P2P engine...")
            
            # Start transport service first to get the actual port
            self._transport = TransportService(
                username=self.username,
                crypto=self.crypto,
                on_message_received=self._handle_message_received
            )
            tcp_port = self._transport.start()
            
            # Start discovery service
            self._discovery = DiscoveryService(
                username=self.username,
                public_key=self.public_key,
                tcp_port=tcp_port,
                on_peer_discovered=self._handle_peer_discovered,
                on_peer_lost=self._handle_peer_lost
            )
            self._discovery.start()
            
            self._running = True
            logger.info(f"P2P engine started on port {tcp_port}")
    
    def stop(self) -> None:
        """Stop all P2P services."""
        with self._lock:
            if not self._running:
                return
            
            logger.info("Stopping P2P engine...")
            
            if self._discovery:
                self._discovery.stop()
                self._discovery = None
            
            if self._transport:
                self._transport.stop()
                self._transport = None
            
            self._running = False
            logger.info("P2P engine stopped")
    
    def get_peers(self) -> Dict[str, Peer]:
        """Get all currently active peers."""
        if self._discovery:
            return self._discovery.get_peers()
        return {}
    
    def get_peer(self, username: str) -> Optional[Peer]:
        """Get a specific peer by username."""
        if self._discovery:
            return self._discovery.get_peer(username)
        return None
    
    def send_message(self, recipient_username: str, message: str) -> bool:
        """
        Send an encrypted message to a peer.
        
        Args:
            recipient_username: The recipient's username
            message: The plaintext message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self._running or not self._transport:
            logger.error("P2P engine not running")
            return False
        
        peer = self.get_peer(recipient_username)
        if not peer:
            logger.error(f"Peer not found: {recipient_username}")
            return False
        
        return self._transport.send_message(
            recipient_ip=peer.ip_address,
            recipient_port=peer.port,
            recipient_public_key=peer.public_key,
            message=message
        )
    
    def broadcast_message(self, message: str) -> Dict[str, bool]:
        """
        Send a message to all known peers.
        
        Args:
            message: The plaintext message to send
            
        Returns:
            Dict mapping username to success status
        """
        results = {}
        for username in self.get_peers():
            results[username] = self.send_message(username, message)
        return results
    
    def _handle_peer_discovered(self, peer: Peer) -> None:
        """Internal handler for peer discovery."""
        if self._on_peer_discovered:
            try:
                self._on_peer_discovered(peer)
            except Exception as e:
                logger.error(f"Error in peer discovered callback: {e}")
    
    def _handle_peer_lost(self, username: str) -> None:
        """Internal handler for peer loss."""
        if self._on_peer_lost:
            try:
                self._on_peer_lost(username)
            except Exception as e:
                logger.error(f"Error in peer lost callback: {e}")
    
    def _handle_message_received(self, sender: str, message: str) -> None:
        """Internal handler for received messages."""
        if self._on_message_received:
            try:
                self._on_message_received(sender, message)
            except Exception as e:
                logger.error(f"Error in message received callback: {e}")
    
    def __enter__(self) -> 'P2PEngine':
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
