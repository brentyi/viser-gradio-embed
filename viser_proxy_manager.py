import asyncio

import httpx
import viser
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response


class ViserProxyManager:
    """Manages Viser server instances for Gradio applications.

    This class handles the creation, retrieval, and cleanup of Viser server instances,
    as well as proxying HTTP and WebSocket requests to the appropriate Viser server.

    Args:
        app: The FastAPI application to which the proxy routes will be added.
        min_local_port: Minimum local port number to use for Viser servers. Defaults to 8000.
            These ports are used only for internal communication and don't need to be publicly exposed.
        max_local_port: Maximum local port number to use for Viser servers. Defaults to 9000.
            These ports are used only for internal communication and don't need to be publicly exposed.
    """

    def __init__(
        self,
        app: FastAPI,
        min_local_port: int = 8000,
        max_local_port: int = 9000,
    ) -> None:
        self._min_port = min_local_port
        self._max_port = max_local_port
        self._server_from_session_hash: dict[str, viser.ViserServer] = {}
        self._last_port = min_local_port - 1  # Track last port tried

        @app.get("/viser/{server_id}/{proxy_path:path}")
        async def proxy(request: Request, server_id: str, proxy_path: str):
            """Proxy HTTP requests to the appropriate Viser server."""
            # Get the local port for this server ID
            server = self._server_from_session_hash.get(server_id)
            if server is None:
                return Response(content="Server not found", status_code=404)

            # Build target URL
            if proxy_path:
                path_suffix = f"/{proxy_path}"
            else:
                path_suffix = "/"

            target_url = f"http://127.0.0.1:{server.get_port()}{path_suffix}"
            if request.url.query:
                target_url += f"?{request.url.query}"

            # Forward request
            async with httpx.AsyncClient() as client:
                # Forward the original headers, but remove any problematic ones
                headers = dict(request.headers)
                headers.pop("host", None)  # Remove host header to avoid conflicts
                headers["accept-encoding"] = "identity"  # Disable compression

                proxied_req = client.build_request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=await request.body(),
                )
                proxied_resp = await client.send(proxied_req, stream=True)

                # Get response headers
                response_headers = dict(proxied_resp.headers)

                # Check if this is an HTML response
                content = await proxied_resp.aread()
                return Response(
                    content=content,
                    status_code=proxied_resp.status_code,
                    headers=response_headers,
                )

        # WebSocket Proxy
        @app.websocket("/viser/{server_id}")
        async def websocket_proxy(websocket: WebSocket, server_id: str):
            """Proxy WebSocket connections to the appropriate Viser server."""
            await websocket.accept()

            server = self._server_from_session_hash.get(server_id)
            if server is None:
                await websocket.close(code=1008, reason="Not Found")
                return

            # Determine target WebSocket URL
            target_ws_url = f"ws://127.0.0.1:{server.get_port()}"

            if not target_ws_url:
                await websocket.close(code=1008, reason="Not Found")
                return

            try:
                # Connect to the target WebSocket
                async with websockets.connect(target_ws_url) as ws_target:
                    # Create tasks for bidirectional communication
                    async def forward_to_target():
                        """Forward messages from the client to the target WebSocket."""
                        try:
                            while True:
                                data = await websocket.receive_bytes()
                                await ws_target.send(data, text=False)
                        except WebSocketDisconnect:
                            try:
                                await ws_target.close()
                            except RuntimeError:
                                pass

                    async def forward_from_target():
                        """Forward messages from the target WebSocket to the client."""
                        try:
                            while True:
                                data = await ws_target.recv(decode=False)
                                await websocket.send_bytes(data)
                        except websockets.exceptions.ConnectionClosed:
                            try:
                                await websocket.close()
                            except RuntimeError:
                                pass

                    # Run both forwarding tasks concurrently
                    forward_task = asyncio.create_task(forward_to_target())
                    backward_task = asyncio.create_task(forward_from_target())

                    # Wait for either task to complete (which means a connection was closed)
                    done, pending = await asyncio.wait(
                        [forward_task, backward_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Cancel the remaining task
                    for task in pending:
                        task.cancel()

            except Exception as e:
                print(f"WebSocket proxy error: {e}")
                await websocket.close(code=1011, reason=str(e))

    def start_server(self, server_id: str) -> viser.ViserServer:
        """Start a new Viser server and associate it with the given server ID.

        Finds an available port within the configured min_local_port and max_local_port range.
        These ports are used only for internal communication and don't need to be publicly exposed.

        Args:
            server_id: The unique identifier to associate with the new server.

        Returns:
            The newly created Viser server instance.

        Raises:
            RuntimeError: If no free ports are available in the configured range.
        """
        import socket

        # Start searching from the last port + 1 (with wraparound)
        port_range_size = self._max_port - self._min_port + 1
        start_port = (
            (self._last_port + 1 - self._min_port) % port_range_size
        ) + self._min_port

        # Try each port once
        for offset in range(port_range_size):
            port = (
                (start_port - self._min_port + offset) % port_range_size
            ) + self._min_port
            try:
                # Check if port is available by attempting to bind to it
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    # Port is available, create server with this port
                    server = viser.ViserServer(port=port)
                    self._server_from_session_hash[server_id] = server
                    self._last_port = port
                    return server
            except OSError:
                # Port is in use, try the next one
                continue

        # If we get here, no ports were available
        raise RuntimeError(
            f"No available local ports in range {self._min_port}-{self._max_port}"
        )

    def get_server(self, server_id: str) -> viser.ViserServer:
        """Retrieve a Viser server instance by its ID.

        Args:
            server_id: The unique identifier of the server to retrieve.

        Returns:
            The Viser server instance associated with the given ID.
        """
        return self._server_from_session_hash[server_id]

    def stop_server(self, server_id: str) -> None:
        """Stop a Viser server and remove it from the manager.

        Args:
            server_id: The unique identifier of the server to stop.
        """
        self._server_from_session_hash.pop(server_id).stop()
