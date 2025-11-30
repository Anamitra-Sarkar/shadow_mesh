#!/usr/bin/env python3
"""
SHADOW-MESH - Serverless, Encrypted, Peer-to-Peer LAN Chat Application

A production-level P2P chat application that allows users on the same network
to discover each other and communicate securely without a central server or
internet connection.

Features:
- UDP broadcast-based peer discovery
- Hybrid RSA/Fernet encryption for secure messaging
- Dark web/IRC terminal-styled GUI
- No central server required

Usage:
    python main.py [username]

If no username is provided, one will be automatically generated.
"""

import argparse
import logging
import sys
from typing import Optional


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SHADOW-MESH - Encrypted P2P LAN Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                  # Start with auto-generated username
    python main.py Ghost_42         # Start with custom username
    python main.py -v               # Start with verbose logging
    python main.py --headless       # Start without GUI (server mode)
        """
    )
    
    parser.add_argument(
        "username",
        nargs="?",
        default=None,
        help="Custom username (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no GUI, just P2P services)"
    )
    
    return parser.parse_args()


def run_headless(username: Optional[str]) -> None:
    """Run SHADOW-MESH in headless mode."""
    from p2p_engine import P2PEngine
    
    def on_peer_discovered(peer):
        print(f"[+] Peer discovered: {peer.username} ({peer.ip_address})")
    
    def on_peer_lost(username):
        print(f"[-] Peer lost: {username}")
    
    def on_message_received(sender, message):
        print(f"[MSG] <{sender}> {message}")
    
    engine = P2PEngine(
        username=username,
        on_peer_discovered=on_peer_discovered,
        on_peer_lost=on_peer_lost,
        on_message_received=on_message_received
    )
    
    print("=" * 60)
    print("  SHADOW-MESH // HEADLESS MODE")
    print("=" * 60)
    print(f"  Username: {engine.username}")
    print(f"  Public Key: {engine.public_key[:50]}...")
    print("=" * 60)
    print()
    print("Starting P2P services...")
    
    try:
        engine.start()
        print(f"Listening on port {engine.tcp_port}")
        print("Press Ctrl+C to exit")
        print()
        
        # Keep running until interrupted
        while True:
            try:
                # Simple command interface
                cmd = input()
                if cmd.startswith("/msg "):
                    parts = cmd[5:].split(" ", 1)
                    if len(parts) == 2:
                        recipient, message = parts
                        if engine.send_message(recipient, message):
                            print(f"[SENT] -> {recipient}: {message}")
                        else:
                            print(f"[ERROR] Failed to send to {recipient}")
                elif cmd == "/peers":
                    peers = engine.get_peers()
                    if peers:
                        print("Active peers:")
                        for name, peer in peers.items():
                            print(f"  - {name} ({peer.ip_address}:{peer.port})")
                    else:
                        print("No peers found")
                elif cmd == "/help":
                    print("Commands:")
                    print("  /msg <user> <message> - Send a message")
                    print("  /peers                - List active peers")
                    print("  /help                 - Show this help")
            except EOFError:
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        engine.stop()


def run_gui(username: Optional[str]) -> None:
    """Run SHADOW-MESH with GUI."""
    from gui import ShadowMeshGUI
    
    app = ShadowMeshGUI(username=username)
    app.run()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(verbose=args.verbose)
    
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║   ███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗     ║")
    print("║   ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║     ║")
    print("║   ███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║     ║")
    print("║   ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║     ║")
    print("║   ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝     ║")
    print("║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝      ║")
    print("║                                                           ║")
    print("║              ███╗   ███╗███████╗███████╗██╗  ██╗          ║")
    print("║              ████╗ ████║██╔════╝██╔════╝██║  ██║          ║")
    print("║              ██╔████╔██║█████╗  ███████╗███████║          ║")
    print("║              ██║╚██╔╝██║██╔══╝  ╚════██║██╔══██║          ║")
    print("║              ██║ ╚═╝ ██║███████╗███████║██║  ██║          ║")
    print("║              ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝          ║")
    print("║                                                           ║")
    print("║        Encrypted Peer-to-Peer LAN Communication           ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    
    try:
        if args.headless:
            run_headless(args.username)
        else:
            run_gui(args.username)
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
