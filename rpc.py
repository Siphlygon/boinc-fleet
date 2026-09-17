"""
A module to handle RPC calls to the BOINC client.
"""

import hashlib
import logging
import socket
import xml

logger = logging.getLogger("boinc-fleet.rpc")

# The byte sequence BOINC uses to indicate the end of a message in RPC communication.
END_TXT = b"\003"

class BOINCClient:
    """
    A class to represent a BOINC client and handle RPC calls.
    """

    def __init__(self, host: str, port: int, timeout: int = 30, password: str = ""):
        """
        Initialize the BOINCClient with the specified parameters.

        Parameters
        ----------
        host : str
            The hostname or IPv4 address of the BOINC client.
        port : int
            The port number of the BOINC client.
        timeout : int, optional
            The timeout in seconds for the connection attempt (default is 30 seconds).
        password : str, optional
            The password for authentication with the BOINC client (default is an empty string).
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.password = password
        self.socket = None

    # == connection == 
    def connect(self) -> None:
        """Connect to the BOINC client via RPC with the specified host and port and store the socket object."""
        try:
            self.socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
            logger.info(f"Connected to BOINC client at {self.host}:{self.port}")
        except socket.error as e:
            logger.error(f"Failed to connect to BOINC client at {self.host}:{self.port}: {e}")
            raise

    def close(self) -> None:
        """Close the connection to the BOINC client."""
        if self.socket:
            self.socket.close()
            self.socket = None

    # == RPC communication ==
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
            logger.error(f"Failure while sending message: {message} \n Error: {e}")
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
            logger.error(f"Failure while receiving response: {e}")
            raise

    def _rpc_call(self, message: str) -> xml.etree.ElementTree.Element:
        """
        Perform an RPC call to the BOINC client.

        Parameters
        ----------
        message : str
            The message to send in the RPC call.

        Returns
        -------
        xml.etree.ElementTree.Element
            The response received from the BOINC client, parsed as an XML element.
        """
        self._send(message)
        reply = self._receive()
        if not reply:
            raise RuntimeError("No response received from BOINC client.")

        return xml.etree.ElementTree.fromstring(reply)

    def request(self, command: str) -> xml.etree.ElementTree.Element:
        """
        Send a no-argument request to the BOINC client and receive a response.

        Parameters
        ----------
        command : str
            The command to send in the request.

        Returns
        -------
        xml.etree.ElementTree.Element
            The response received from the BOINC client, parsed as an XML element.
        """
        return self._rpc_call(f"<{command}/>")

    # == authentication ==
    def authenticate(self):
        """
        Authenticate with the BOINC client using the provided password.

        Connects to the BOINC client, requests a nonce, computes a hash of the nonce and password,
        and sends it back for verification.

        Raises
        ------
        PermissionError
            If authentication fails due to an incorrect password.
        """
        # Ask for the nonce from the BOINC client
        nonce = self._rpc_call("<auth1/>").findtext("nonce")

        # Compute the hash of the nonce and password, and send it back to the BOINC client for verification
        digest = hashlib.md5((nonce + self.password).encode()).hexdigest()
        reply = self._rpc_call(f"<auth2><nonce_hash>{digest}</nonce_hash></auth2>")

        if reply.find("authorized") is None:
            raise PermissionError("authentication failed — wrong RPC password?")
