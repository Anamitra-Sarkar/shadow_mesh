"""
SHADOW-MESH GUI
Dark Web / IRC Terminal styled interface using customtkinter.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from discovery import Peer
from p2p_engine import P2PEngine

logger = logging.getLogger(__name__)


class ShadowMeshGUI:
    """Main GUI for SHADOW-MESH application."""
    
    # Color scheme - Dark Web / IRC Terminal style
    COLORS = {
        "bg_dark": "#0a0a0a",
        "bg_panel": "#0d0d0d",
        "bg_input": "#1a1a1a",
        "text_primary": "#00ff00",
        "text_secondary": "#00cc00",
        "text_muted": "#008800",
        "text_system": "#00ffff",
        "text_error": "#ff0000",
        "text_warning": "#ffff00",
        "border": "#003300",
        "highlight": "#004400",
    }
    
    FONT_FAMILY = "Courier"
    FONT_SIZE = 12
    TITLE_FONT_SIZE = 14
    
    def __init__(self, username: Optional[str] = None) -> None:
        """
        Initialize the GUI.
        
        Args:
            username: Optional username override
        """
        self._username = username
        self._engine: Optional[P2PEngine] = None
        self._selected_peer: Optional[str] = None
        self._is_running = False
        
        # Set up the main window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.root = ctk.CTk()
        self.root.title("SHADOW-MESH // ENCRYPTED P2P TERMINAL")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(fg_color=self.COLORS["bg_dark"])
        
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)
        self.root.grid_rowconfigure(1, weight=1)
        
        self._setup_header()
        self._setup_peer_panel()
        self._setup_chat_panel()
        self._setup_input_panel()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_header(self) -> None:
        """Set up the header bar."""
        header = ctk.CTkFrame(
            self.root,
            fg_color=self.COLORS["bg_panel"],
            corner_radius=0,
            height=60
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)
        
        # ASCII art title
        title_text = "╔═══════════════════════════════════════╗\n║  SHADOW-MESH // ENCRYPTED P2P NETWORK  ║\n╚═══════════════════════════════════════╝"
        title = ctk.CTkLabel(
            header,
            text=title_text,
            font=(self.FONT_FAMILY, self.TITLE_FONT_SIZE, "bold"),
            text_color=self.COLORS["text_primary"],
            justify="center"
        )
        title.pack(side="left", padx=20)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            header,
            text="[ INITIALIZING... ]",
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            text_color=self.COLORS["text_system"]
        )
        self.status_label.pack(side="right", padx=20)
    
    def _setup_peer_panel(self) -> None:
        """Set up the left panel showing nearby nodes."""
        panel_frame = ctk.CTkFrame(
            self.root,
            fg_color=self.COLORS["bg_panel"],
            corner_radius=0,
            width=300
        )
        panel_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        panel_frame.grid_propagate(False)
        
        # Panel header
        header = ctk.CTkLabel(
            panel_frame,
            text="═══ NEARBY NODES ═══",
            font=(self.FONT_FAMILY, self.FONT_SIZE, "bold"),
            text_color=self.COLORS["text_primary"]
        )
        header.pack(pady=(10, 5), padx=10)
        
        # Peer list
        self.peer_listbox = ctk.CTkScrollableFrame(
            panel_frame,
            fg_color=self.COLORS["bg_dark"],
            corner_radius=5,
            border_width=1,
            border_color=self.COLORS["border"]
        )
        self.peer_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Store peer buttons
        self.peer_buttons: dict = {}
        
        # Placeholder text
        self.no_peers_label = ctk.CTkLabel(
            self.peer_listbox,
            text="[ Scanning network... ]",
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            text_color=self.COLORS["text_muted"]
        )
        self.no_peers_label.pack(pady=20)
    
    def _setup_chat_panel(self) -> None:
        """Set up the right panel for chat messages."""
        panel_frame = ctk.CTkFrame(
            self.root,
            fg_color=self.COLORS["bg_panel"],
            corner_radius=0
        )
        panel_frame.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        panel_frame.grid_columnconfigure(0, weight=1)
        panel_frame.grid_rowconfigure(1, weight=1)
        
        # Chat header
        self.chat_header = ctk.CTkLabel(
            panel_frame,
            text="═══ ENCRYPTED CHANNEL ═══",
            font=(self.FONT_FAMILY, self.FONT_SIZE, "bold"),
            text_color=self.COLORS["text_primary"]
        )
        self.chat_header.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="ew")
        
        # Chat display
        self.chat_display = ctk.CTkTextbox(
            panel_frame,
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            fg_color=self.COLORS["bg_dark"],
            text_color=self.COLORS["text_primary"],
            border_width=1,
            border_color=self.COLORS["border"],
            corner_radius=5,
            wrap="word",
            state="disabled"
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    
    def _setup_input_panel(self) -> None:
        """Set up the message input panel."""
        input_frame = ctk.CTkFrame(
            self.root,
            fg_color=self.COLORS["bg_panel"],
            corner_radius=0,
            height=80
        )
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        input_frame.grid_propagate(False)
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Input entry
        self.message_entry = ctk.CTkEntry(
            input_frame,
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            fg_color=self.COLORS["bg_input"],
            text_color=self.COLORS["text_primary"],
            border_width=1,
            border_color=self.COLORS["border"],
            corner_radius=5,
            placeholder_text="Type message here... (select a peer first)",
            height=40
        )
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=20)
        self.message_entry.bind("<Return>", self._on_send_message)
        
        # Send button
        self.send_button = ctk.CTkButton(
            input_frame,
            text="[ TRANSMIT ]",
            font=(self.FONT_FAMILY, self.FONT_SIZE, "bold"),
            fg_color=self.COLORS["highlight"],
            hover_color=self.COLORS["border"],
            text_color=self.COLORS["text_primary"],
            border_width=1,
            border_color=self.COLORS["text_muted"],
            corner_radius=5,
            width=120,
            height=40,
            command=self._on_send_message
        )
        self.send_button.grid(row=0, column=1, padx=(5, 10), pady=20)
    
    def _add_chat_message(
        self, 
        message: str, 
        sender: Optional[str] = None,
        is_system: bool = False,
        is_own: bool = False
    ) -> None:
        """Add a message to the chat display."""
        self.chat_display.configure(state="normal")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if is_system:
            formatted = f"[{timestamp}] {message}\n"
            self.chat_display.insert("end", formatted)
        elif is_own:
            formatted = f"[{timestamp}] <YOU> {message}\n"
            self.chat_display.insert("end", formatted)
        else:
            formatted = f"[{timestamp}] <{sender}> {message}\n"
            self.chat_display.insert("end", formatted)
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
    
    def _show_decryption_animation(self, sender: str, message: str) -> None:
        """Show decryption animation before displaying message."""
        def animate():
            # Show decrypting message
            self.chat_display.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_display.insert("end", f"[{timestamp}] <{sender}> [DECRYPTING...]")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")
            
            # Wait for effect
            time.sleep(0.5)
            
            # Remove the decrypting line and show actual message
            self.root.after(0, lambda: self._replace_last_message(sender, message))
        
        threading.Thread(target=animate, daemon=True).start()
    
    def _replace_last_message(self, sender: str, message: str) -> None:
        """Replace the last message (decrypting animation) with actual message."""
        self.chat_display.configure(state="normal")
        
        # Get current content
        content = self.chat_display.get("1.0", "end")
        lines = content.split("\n")
        
        # Remove the last non-empty line (the [DECRYPTING...] message)
        for i in range(len(lines) - 1, -1, -1):
            if "[DECRYPTING...]" in lines[i]:
                lines[i] = ""
                break
        
        # Clear and rewrite
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("1.0", "\n".join(lines))
        
        # Add the actual message
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert("end", f"[{timestamp}] <{sender}> {message}\n")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
    
    def _update_peer_list(self) -> None:
        """Update the peer list display."""
        if not self._engine:
            return
        
        peers = self._engine.get_peers()
        
        # Clear existing buttons
        for widget in self.peer_listbox.winfo_children():
            widget.destroy()
        self.peer_buttons.clear()
        
        if not peers:
            self.no_peers_label = ctk.CTkLabel(
                self.peer_listbox,
                text="[ No nodes detected ]",
                font=(self.FONT_FAMILY, self.FONT_SIZE),
                text_color=self.COLORS["text_muted"]
            )
            self.no_peers_label.pack(pady=20)
            return
        
        for username, peer in peers.items():
            btn = ctk.CTkButton(
                self.peer_listbox,
                text=f"► {username}",
                font=(self.FONT_FAMILY, self.FONT_SIZE),
                fg_color="transparent",
                hover_color=self.COLORS["highlight"],
                text_color=self.COLORS["text_secondary"],
                anchor="w",
                height=30,
                command=lambda u=username: self._select_peer(u)
            )
            btn.pack(fill="x", pady=2, padx=5)
            self.peer_buttons[username] = btn
        
        # Update selection highlighting
        self._highlight_selected_peer()
    
    def _select_peer(self, username: str) -> None:
        """Select a peer for chatting."""
        self._selected_peer = username
        self._highlight_selected_peer()
        
        self.chat_header.configure(
            text=f"═══ ENCRYPTED CHANNEL // {username} ═══"
        )
        
        self._add_chat_message(
            f"Secure channel established with {username}",
            is_system=True
        )
    
    def _highlight_selected_peer(self) -> None:
        """Update visual highlighting of selected peer."""
        for username, btn in self.peer_buttons.items():
            if username == self._selected_peer:
                btn.configure(
                    fg_color=self.COLORS["highlight"],
                    text_color=self.COLORS["text_primary"]
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.COLORS["text_secondary"]
                )
    
    def _on_send_message(self, event=None) -> None:
        """Handle sending a message."""
        message = self.message_entry.get().strip()
        
        if not message:
            return
        
        if not self._selected_peer:
            self._add_chat_message(
                "ERROR: Select a peer first",
                is_system=True
            )
            return
        
        if not self._engine:
            self._add_chat_message(
                "ERROR: Engine not initialized",
                is_system=True
            )
            return
        
        # Clear input
        self.message_entry.delete(0, "end")
        
        # Send message
        success = self._engine.send_message(self._selected_peer, message)
        
        if success:
            self._add_chat_message(message, is_own=True)
        else:
            self._add_chat_message(
                f"ERROR: Failed to send message to {self._selected_peer}",
                is_system=True
            )
    
    def _on_peer_discovered(self, peer: Peer) -> None:
        """Handle peer discovery callback."""
        self.root.after(0, self._update_peer_list)
        self.root.after(0, lambda: self._add_chat_message(
            f"Node connected: {peer.username} ({peer.ip_address})",
            is_system=True
        ))
    
    def _on_peer_lost(self, username: str) -> None:
        """Handle peer lost callback."""
        self.root.after(0, self._update_peer_list)
        self.root.after(0, lambda: self._add_chat_message(
            f"Node disconnected: {username}",
            is_system=True
        ))
        
        # Clear selection if selected peer was lost
        if self._selected_peer == username:
            self._selected_peer = None
            self.root.after(0, lambda: self.chat_header.configure(
                text="═══ ENCRYPTED CHANNEL ═══"
            ))
    
    def _on_message_received(self, sender: str, message: str) -> None:
        """Handle incoming message callback."""
        self.root.after(0, lambda: self._show_decryption_animation(sender, message))
    
    def _on_close(self) -> None:
        """Handle window close."""
        self._is_running = False
        
        if self._engine:
            self._engine.stop()
        
        self.root.destroy()
    
    def run(self) -> None:
        """Start the application."""
        self._is_running = True
        
        # Initialize and start the P2P engine
        self._engine = P2PEngine(
            username=self._username,
            on_peer_discovered=self._on_peer_discovered,
            on_peer_lost=self._on_peer_lost,
            on_message_received=self._on_message_received
        )
        self._engine.start()
        
        # Update status
        self.status_label.configure(
            text=f"[ ONLINE // {self._engine.username} // PORT {self._engine.tcp_port} ]"
        )
        
        # Add startup message
        self._add_chat_message(
            f"SHADOW-MESH initialized. Your identity: {self._engine.username}",
            is_system=True
        )
        self._add_chat_message(
            "Scanning network for nodes...",
            is_system=True
        )
        
        # Start periodic peer list update
        self._schedule_peer_refresh()
        
        # Run the main loop
        self.root.mainloop()
    
    def _schedule_peer_refresh(self) -> None:
        """Schedule periodic peer list refresh."""
        if self._is_running:
            self._update_peer_list()
            self.root.after(2000, self._schedule_peer_refresh)


def main() -> None:
    """Main entry point for the GUI application."""
    import sys
    
    username = None
    if len(sys.argv) > 1:
        username = sys.argv[1]
    
    app = ShadowMeshGUI(username=username)
    app.run()


if __name__ == "__main__":
    main()
