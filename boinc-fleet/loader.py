"""
A module that loads the configuration file for the project and provides a function to retrieve the configuration data.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .logger import get_logger

logger = get_logger("boinc-fleet.loader")
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"

@dataclass
class NodeConfig:
    """
    A dataclass to represent the configuration of a single node.
    """
    name: str               # The name of the node
    host: str               # The hostname or IP address of the node
    port: int               # The port number for the node's RPC interface
    password: str = None    # Optional password for the node

    @classmethod
    def from_dict(cls, data: dict) -> 'NodeConfig':
        """
        Create a NodeConfig instance from a dictionary.

        Parameters
        ----------
        data : dict
            A dictionary containing the node configuration data.
        
        Returns
        -------
        NodeConfig
            An instance of NodeConfig created from the provided dictionary.
        """
        return cls(
            name=data.get("name"),
            host=data.get("host"),
            port=data.get("port"),
            password=data.get("password")
        )


@dataclass
class Config:
    """
    A dataclass to represent the overall configuration of the project.
    """
    poll_interval: int         # The interval in seconds between polling the nodes
    timeout: int               # The timeout value for RPC requests
    default_password: str      # The default password for nodes that do not have a specific password set
    nodes: list[NodeConfig]    # A list of NodeConfig instances representing the nodes in the configuration

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """
        Create a Config instance from a dictionary.

        Parameters
        ----------
        data : dict
            A dictionary containing the overall configuration data.
        
        Returns
        -------
        Config
            An instance of Config created from the provided dictionary.
        """
        nodes = [NodeConfig.from_dict(node) for node in data.get("nodes", [])]
        return cls(
            poll_interval=data.get("poll_interval"),
            timeout=data.get("timeout"),
            default_password=data.get("default_password"),
            nodes=nodes
        )


def load_config(file_path: Path = _DEFAULT_CONFIG_PATH) -> Config:
    """
    Load the configuration from a JSON file.

    Parameters
    ----------
    file_path : Path
        The path to the JSON configuration file.
    
    Returns
    -------
    Config
        The configuration data as a Config instance.
    """
    with open(file_path, 'r') as file:
        config = json.load(file)
    logger.info(f"Loaded configuration from {file_path}")
    return Config.from_dict(config)


if __name__ == "__main__":
    # Example usage: Load the configuration and print it
    config = load_config()
    print(config)
