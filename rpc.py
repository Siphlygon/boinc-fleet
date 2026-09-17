"""
A module to handle RPC calls to the BOINC client.
"""

import logging
import socket

logger = logging.getLogger("boinc-fleet.rpc")

# The byte sequence BOINC uses to indicate the end of a message in RPC communication.
END_TXT = b"\003"

class BOINCClient:
    """
    A class to represent a BOINC client and handle RPC calls.
    """

    def __init__(self, host: str, port: int, timeout: int = 30):
        """
        Initialize the BOINCClient with the specified host, port, and timeout.

        Parameters
        ----------
        host : str
            The hostname or IPv4 address of the BOINC client.
        port : int
            The port number of the BOINC client.
        timeout : int, optional
            The timeout in seconds for the connection attempt (default is 30 seconds).
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None

    def connect(self) -> None:
        """Connect to the BOINC client via RPC with the specified host and port and store the socket object."""
        try:
            self.socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
            logger.info(f"Connected to BOINC client at {self.host}:{self.port}")
        except socket.error as e:
            logger.error(f"Failed to connect to BOINC client at {self.host}:{self.port}: {e}")
            raise

    def _send(self, message: str):
        """
        Send a message to the BOINC client via RPC, wrapping the message in the appropriate XML tags.

        Parameters
        ----------
        message : str
            The message to send.
        """
        if not self.socket:
            raise RuntimeError("Not connected to BOINC client.")
        try:
            message = f"<boinc_gpu_rpc_request>\n{message}\n</boinc_gpu_rpc_request>"
            self.socket.sendall(message.encode('utf-8') + END_TXT)
            logger.debug(f"Sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send message: {message} \n Error: {e}")
            raise

    def _receive(self) -> str:
        """
        Receive a response from the BOINC client via RPC.

        Listens on the socket until it receives the END_TXT byte sequence, indicating the end of the message.

        Returns
        -------
        str
            The response received from the BOINC client.
        """
        if not self.socket:
            raise RuntimeError("Not connected to BOINC client.")
        try:
            response = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                if END_TXT in chunk:
                    break
            response_str = response.decode('utf-8').rstrip('\003')
            logger.debug(f"Received response: {response_str}")
            return response_str
        except Exception as e:
            logger.error(f"Failed to receive response: {e}")
            raise
