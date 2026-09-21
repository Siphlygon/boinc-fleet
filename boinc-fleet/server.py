"""
A module to create and manage a HTTP server which will return information about the BOINC client on a given host.    
"""

import http.server
import json
from pathlib import Path

from . import parse, rpc
from .logger import get_logger

# Path to the index.html file which will be served when accessing the root path of the server
_INDEX_HTML = Path(__file__).parent / "static" / "index.html"

logger = get_logger("boinc-fleet.server")

class BOINCRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    A GET request handler for the BOINC HTTP server.
    """

    def do_GET(self):
        """
        Handles GET requests to the server.
        
        Supports paths for "/api/nodes" to fetch summary information from the BOINC client and "/" or "/index.html" to
        serve a simple web page. Returns a 404 error for unsupported paths.
        """
        # Handle the /api/nodes path to fetch summary information from the BOINC client
        if self.path == "/api/nodes":
            # Read information locally or use standards
            host = "127.0.0.1"
            port = 31416
            password = Path("/var/lib/boinc-client/gui_rpc_auth.cfg").read_text().strip()
            try:
                summary = fetch_summary(host, port, password)
                response = jsonify_summary(summary)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Error fetching summary.')
                logger.error(f"Error fetching summary: {e}")
                return

        # Serve the web page for the index.html, which will display the summary information in a user-friendly format
        if self.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            # OPen and send the HTML file
            with open(_INDEX_HTML, 'r') as f:
                self.wfile.write(f.read().encode('utf-8'))
            return

        # Otherwise, we have an unsupported path
        self.send_response(404)
        self.end_headers()
        logger.debug("Not Found")
        self.wfile.write(b'Path Not Found')
        return


def fetch_summary(host: str, port: int, password: str) -> dict:
    """
    Fetches the summary information from the BOINC client on the given host and port, authenticating using the provided
    password.

    Parameters
    ----------
    host : str
        The hostname or IP address of the BOINC client.
    port : int
        The port number on which the BOINC client is listening.
    password : str
        The password used for authenticating with the BOINC client.
    
    Returns
    -------
    dict
        A dictionary containing the summary information of the BOINC client, including dataclass objects.
    """
    # Start and connect to the BOINC client
    client = rpc.BOINCClient(host=host, port=port, password=password)
    client.connect()
    client.authenticate()

    # Use the get_state command and summarise
    reply = client.request("get_state")
    summary = parse.summarise_state(reply)
    return summary


def jsonify_summary(summary: dict) -> bytes:
    """
    Converts the summary dictionary into a JSON string representation, encoding it in UTF-8.

    Parameters
    ----------
    summary : dict
        The summary information of the BOINC client.
    
    Returns
    -------
    bytes
        A JSON string representation of the summary, encoded in UTF-8.
    """
    return json.dumps(summary, default=lambda o: o.__dict__, indent=4).encode('utf-8')


def main():
    """
    Starts the BOINC HTTP server on the specified host and port.
    
    The server will handle incoming GET requests to fetch summary information from the BOINC client or be served a
    simple web page. It will run indefinitely until interrupted.
    """
    server_address = ('', 8000)  # Listen on all interfaces, port 8000
    httpd = http.server.ThreadingHTTPServer(server_address, BOINCRequestHandler)
    logger.info(f'Starting BOINC HTTP server on {server_address[0]}:{server_address[1]}...')
    httpd.serve_forever()


if __name__ == "__main__":
    main()
