"""
Real-Time Dashboard Server

Provides WebSocket-based real-time monitoring of agent status.
Broadcasts state updates to connected web clients when changes occur.
Serves static HTML/CSS/JS files via HTTP on the same port.
"""

import asyncio
import json
import logging
import mimetypes
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

import websockets
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from context_md.config import Config
from context_md.state import State

logger = logging.getLogger(__name__)


# HTTP Handler for static files
async def http_handler(path: str, request_headers) -> tuple:
    """Handle HTTP requests for static files."""
    static_dir = Path(__file__).parent / "static"
    
    # Default to index
    if path == "/" or path == "":
        path = "/dashboard.html"
    
    # Security: prevent directory traversal
    file_path = (static_dir / path.lstrip("/")).resolve()
    if not str(file_path).startswith(str(static_dir)):
        return (404, [], b"Not Found")
    
    # Serve file if exists
    if file_path.exists() and file_path.is_file():
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"
        
        with open(file_path, "rb") as f:
            body = f.read()
        
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ]
        return (200, headers, body)
    
    return (404, [], b"Not Found")


class StateChangeHandler(FileSystemEventHandler):
    """Monitors .agent-context directory for changes."""
    
    def __init__(self, callback):
        self.callback = callback
        self._last_modified = {}
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        # Debounce rapid fire events
        path = event.src_path
        now = datetime.now(timezone.utc).timestamp()
        last = self._last_modified.get(path, 0)
        
        if now - last < 0.5:  # Ignore events within 500ms
            return
        
        self._last_modified[path] = now
        
        # Trigger callback for state changes
        if path.endswith('state.json') or path.endswith('.md'):
            logger.debug(f"File change detected: {path}")
            asyncio.create_task(self.callback())
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            logger.debug(f"File created: {event.src_path}")
            asyncio.create_task(self.callback())


class DashboardServer:
    """WebSocket server for real-time dashboard."""
    
    def __init__(self, repo_root: Path, host: str = "localhost", port: int = 8765):
        self.repo_root = repo_root
        self.host = host
        self.port = port
        self.clients: Set[websockets.ServerProtocol] = set()
        self.observer: Optional[Observer] = None
        self.state = State(repo_root)
        self.config = Config(repo_root)
    
    async def register(self, websocket: websockets.ServerProtocol):
        """Register a new client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial status immediately
        await self.send_status_update(websocket)
    
    async def unregister(self, websocket: websockets.ServerProtocol):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def send_status_update(self, websocket: Optional[websockets.ServerProtocol] = None):
        """Send status update to client(s)."""
        # Reload state to get latest data
        self.state = State(self.repo_root)
        
        # Collect status data (reuse existing logic from status.py)
        data = self._collect_status()
        
        message = json.dumps({
            "type": "status_update",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "data": data
        })
        
        if websocket:
            # Send to specific client
            await websocket.send(message)
        else:
            # Broadcast to all clients
            if self.clients:
                await asyncio.gather(
                    *[client.send(message) for client in self.clients],
                    return_exceptions=True
                )
    
    def _collect_status(self) -> Dict[str, Any]:
        """Collect current status (adapted from status.py)."""
        from context_md.commands.status import _collect_status
        return _collect_status(self.repo_root, self.state, self.config)
    
    async def handle_client_message(self, websocket: websockets.ServerProtocol, message: str):
        """Handle incoming messages from clients."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "ping":
                # Respond with pong
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }))
            elif msg_type == "request_update":
                # Send current status
                await self.send_status_update(websocket)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def ws_handler(self, websocket: websockets.ServerProtocol):
        """WebSocket connection handler."""
        await self.register(websocket)
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def process_request(self, path, request_headers):
        """Process HTTP requests for static files."""
        if path == "/ws":
            # Let WebSocket upgrade proceed
            return None
        
        # Serve static files
        return await http_handler(path, request_headers)
    
    async def broadcast_update(self):
        """Broadcast status update to all clients."""
        await self.send_status_update()
    
    def start_file_watcher(self):
        """Start watching .agent-context directory for changes."""
        watch_dir = self.repo_root / ".agent-context"
        
        if not watch_dir.exists():
            logger.warning(f"Watch directory does not exist: {watch_dir}")
            return
        
        event_handler = StateChangeHandler(self.broadcast_update)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(watch_dir), recursive=True)
        self.observer.start()
        logger.info(f"File watcher started on: {watch_dir}")
    
    def stop_file_watcher(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")
    
    async def serve(self):
        """Start the WebSocket server with HTTP support."""
        # Start file watcher
        self.start_file_watcher()
        
        try:
            async with websockets.serve(
                self.ws_handler,
                self.host,
                self.port,
                process_request=self.process_request
            ):
                logger.info(f"Dashboard server started at http://{self.host}:{self.port}")
                await asyncio.Future()  # Run forever
        finally:
            self.stop_file_watcher()
    
    @staticmethod
    def open_browser(port: int):
        """Open dashboard in default browser."""
        url = f"http://localhost:{port}"
        try:
            webbrowser.open(url)
            logger.info(f"Opened browser at {url}")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")


async def start_dashboard(repo_root: Path, host: str = "localhost", port: int = 8765, open_browser: bool = True):
    """Start the dashboard server.
    
    Args:
        repo_root: Repository root directory
        host: Server host (default: localhost)
        port: Server port (default: 8765)
        open_browser: Whether to open browser automatically
    """
    server = DashboardServer(repo_root, host, port)
    
    if open_browser:
        # Open browser after slight delay
        asyncio.create_task(delayed_browser_open(port, delay=1.0))
    
    await server.serve()


async def delayed_browser_open(port: int, delay: float = 1.0):
    """Open browser after a delay to ensure server is ready."""
    await asyncio.sleep(delay)
    DashboardServer.open_browser(port)
