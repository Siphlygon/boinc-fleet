"""
A module to parse a XML `get_state` reply and return clean Python objects.    

The objects returned are dataclasses that can be used to access the data in a structured way. They do not encompass
all possible XML fields returned by the BOINC client, but only the most relevant ones. The dataclasses can be extended
to include additional fields as needed.
"""

import builtins
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from .logger import get_logger

logger = get_logger("boinc-fleet.parse")


def _convert_xml_value(value: str | None, annotation: Any) -> Any:
    """
    Convert XML text to the type declared by a dataclass field.

    Used to dynamically convert XML text to the type declared by a dataclass field. This function handles basic types
    like str, int, float, and bool, as well as optional types (Union with None).
    
    Parameters
    ----------
    value : str | None
        The XML text to convert. Can be None if the XML element is missing or empty.
    annotation : Any
        The type annotation of the dataclass field. This can be a basic type or a Union with None for optional fields.
    
    Returns
    -------
    Any
        The converted value, which will be of the type specified by the annotation. If the value is None, it will
        return None. If the value cannot be converted to the specified type, a ValueError will be raised.
    """
    if value is None:
        return None

    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        annotation = next(
            (option for option in get_args(annotation) if option is not type(None)),
            str,
        )

    if annotation is str or annotation is Any:
        return value
    if annotation is bool:
        return value.lower() in {"1", "true", "yes"}
    if annotation is int:
        numeric_value = float(value)
        if not numeric_value.is_integer():
            raise ValueError(f"Expected an integer XML value, got {value!r}")
        return int(numeric_value)
    if annotation is float:
        return float(value)
    return value


class XMLStructure:
    """
    A base class for XML structures that can be created from an XML element.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_xml(cls, xml_element: ET.Element):
        """
        Create an instance of the class from an XML element, mapping the child elements to the class attributes.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        cls
            An instance of the class with attributes populated from the XML element.
        """
        field_names = set(getattr(cls, '__dataclass_fields__', {}))
        type_hints = get_type_hints(cls)
        kwargs = {
            child.tag: _convert_xml_value(child.text, type_hints[child.tag])
            for child in xml_element
            if child.tag in field_names
        }
        return cls(**kwargs)

    def __repr__(self) -> str:
        """
        Return a string representation of the object, showing its class name and attributes.

        Returns
        -------
        str
            A string representation of the object.
        """
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


@dataclass
class Coproc(XMLStructure):
    """
    A class to represent a coprocessor (e.g., GPU) from the BOINC client.
    """
    name: str             # the name of the GPU or coprocessor
    available_ram: int    # the available RAM on the GPU or coprocessor


@dataclass
class HostInfo(XMLStructure):
    """
    A class to represent the host information from the BOINC client.
    """
    domain_name: str                # the domain name of the host
    ip_addr: str                    # the IP address of the host
    p_ncpus: int                    # the number of CPUs on the host
    p_vendor: str                   # the CPU vendor
    p_model: str                    # the CPU model
    os_version: str                 # the operating system version
    coprocs: list[Coproc | None]    # List of coprocessors (e.g., GPUs) with their details

    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> "HostInfo":
        """
        Create an instance of HostInfo from an XML element, with special handling for the <coproc> elements.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        HostInfo
            An instance of HostInfo with attributes populated from the XML element.
        """
        coprocs_element = xml_element.find('coprocs')
        # todo: handle other coproc types (e.g., OpenCL, Vulkan) if needed
        coprocs = [
            Coproc.from_xml(c)
            for c in coprocs_element.findall('coproc_cuda')] \
            if coprocs_element is not None else []
        field_names = set(getattr(cls, '__dataclass_fields__', {}))
        type_hints = get_type_hints(cls)
        kwargs = {
            child.tag: _convert_xml_value(child.text, type_hints[child.tag])
            for child in xml_element
            if child.tag != 'coprocs' and child.tag in field_names
        }
        return cls(coprocs=coprocs, **kwargs)

    def display(self, logger: logging.Logger | None = None) -> None:
        """
        Display the host information in a human-readable format.

        Parameters
        ----------
        logger : logging.Logger, optional
            A logger to use for output. If not provided, the built-in print function will be used.
        """
        # Optionally override the default print function with a logger if provided
        print = logger.info if logger else builtins.print

        print("===== Host Information =====")
        print(f"Domain Name: {self.domain_name}")
        print(f"IP Address: {self.ip_addr}")
        print(f"Number of CPUs: {self.p_ncpus}")
        print(f"CPU Vendor: {self.p_vendor}")
        print(f"CPU Model: {self.p_model}")
        print(f"OS Version: {self.os_version}")
        if self.coprocs:
            print("Coprocessors:")
            for coproc in self.coprocs:
                print(f"  - Name: {coproc.name}, Available RAM: {coproc.available_ram / (1024**3):.2f} GB")
        else:
            print("No coprocessors found.")


@dataclass
class ProjectInfo(XMLStructure):
    """
    A class to represent the project information from the BOINC client.
    """
    # Project information
    project_name: str            # the name of the project
    master_url: str              # the URL of the project's master server

    # User information (one user per project, may have many hosts)
    user_name: str               # the name of the user associated with the project
    user_total_credit: float     # the total credit earned by the user in the project
    user_expavg_credit: float    # the exponentially averaged credit for the user in the project

    # Host information (identifies a specific machine associated with a user)
    hostid: str                  # the unique identifier for the host in the project
    host_total_credit: float   # the total credit earned by the host in the project
    host_expavg_credit: float    # the exponentially averaged credit for the host in the project

    # Team information (optional, may not be present in all replies)
    team_name: str | None = None               # the name of the team associated with the project
    team_total_credit: float | None = None     # the total credit earned by the team in the project
    team_expavg_credit: float | None = None    # the exponentially averaged credit for the team in the project

    def display(self, logger: logging.Logger | None = None) -> None:
        """
        Display the project information in a human-readable format.

        Parameters
        ----------
        logger : logging.Logger, optional
            A logger to use for output. If not provided, the built-in print function will be used.
        """
        # Optionally override the default print function with a logger if provided
        print = logger.info if logger else builtins.print

        print("===== Project Information =====")
        print(f"Project Name: {self.project_name}")
        print(f"Master URL: {self.master_url}")
        print(f"User Name: {self.user_name}")
        print(f"User Total Credit: {self.user_total_credit}")
        print(f"User Expavg Credit: {self.user_expavg_credit}")
        print(f"Host ID: {self.hostid}")
        print(f"Host Total Credit: {self.host_total_credit}")
        print(f"Host Expavg Credit: {self.host_expavg_credit}")
        if self.team_name:
            print(f"Team Name: {self.team_name}")
            print(f"Team Total Credit: {self.team_total_credit}")
            print(f"Team Expavg Credit: {self.team_expavg_credit}")


@dataclass
class ActiveTask(XMLStructure):
    """
    A class to represent an active task from the BOINC client.
    """
    active_task_state: int       # the current state of the task (e.g., "running", "ready_to_report")
    fraction_done: float         # the fraction of the task that is completed (0.0 to 1.0)
    elapsed_time: float          # the elapsed time for the task in seconds

    def display(self, logger: logging.Logger | None = None) -> None:
        """
        Display the active task information in a human-readable format.

        Parameters
        ----------
        logger : logging.Logger, optional
            A logger to use for output. If not provided, the built-in print function will be used.
        """
        # Optionally override the default print function with a logger if provided
        print = logger.info if logger else builtins.print

        print("----- Active Task Information -----")
        print(f"Active Task State: {self.active_task_state}")
        print(f"Fraction Done: {self.fraction_done}")
        print(f"Elapsed Time: {self.elapsed_time}")


@dataclass
class TaskInfo(XMLStructure):
    """
    A class to represent the task information from the BOINC client.
    """
    name: str                              # the name of the task
    wu_name: str                           # the work unit name associated with the task
    project_url: str                       # the URL of the project associated with the task
    estimated_cpu_time_remaining: float    # the estimated runtime for the task in seconds
    report_deadline: float                 # the report deadline for the task
    active_task: ActiveTask | None         # the active task details, if any

    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> "TaskInfo":
        """
        Create an instance of TaskInfo from an XML element, with special handling for the <active_task> element.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        TaskInfo
            An instance of TaskInfo with attributes populated from the XML element.
        """
        active_task_element = xml_element.find('active_task')
        active_task = ActiveTask.from_xml(active_task_element) if active_task_element is not None else None
        field_names = set(getattr(cls, '__dataclass_fields__', {}))
        type_hints = get_type_hints(cls)
        kwargs = {
            child.tag: _convert_xml_value(child.text, type_hints[child.tag])
            for child in xml_element
            if child.tag != 'active_task' and child.tag in field_names
        }
        return cls(active_task=active_task, **kwargs)

    def display(self, logger: logging.Logger | None = None) -> None:
        """
        Display the task information in a human-readable format.

        Parameters
        ----------
        logger : logging.Logger, optional
            A logger to use for output. If not provided, the built-in print function will be used.
        """
        # Optionally override the default print function with a logger if provided
        print = logger.info if logger else builtins.print

        print("===== Task Information =====")
        print(f"Task Name: {self.name}")
        print(f"Work Unit Name: {self.wu_name}")
        print(f"Project URL: {self.project_url}")
        print(f"Estimated CPU Time Remaining: {self.estimated_cpu_time_remaining}")
        print(f"Report Deadline: {self.report_deadline}")
        if self.active_task:
            self.active_task.display(logger=logger)


def _get_client_state(reply: ET.Element) -> ET.Element:
    """
    Return the <client_state> element from a BOINC reply or itself.
    
    Parameters
    ----------
    reply : ET.Element
        The XML element representing the BOINC reply.
    
    Returns
    -------
    ET.Element
        The <client_state> element if present, otherwise the original reply element.
    """
    client_state = reply.find('client_state')
    return client_state if client_state is not None else reply


def parse_projects(client_state: ET.Element) -> list[ProjectInfo]:
    """
    Parse the <project> field returned from the get_state reply.

    Parameters
    ----------
    client_state : ET.Element
        The XML element representing the get_state reply.

    Returns
    -------
    list of ProjectInfo
        A list of ProjectInfo objects, each representing a project with its details.
    """
    client_state = _get_client_state(client_state)
    projects = []
    for project in client_state.findall('project'):
        projects.append(ProjectInfo.from_xml(project))
    return projects


def parse_host_info(client_state: ET.Element) -> HostInfo:
    """
    Parse the host information from the get_state reply.

    Parameters
    ----------
    client_state : ET.Element
        The XML element representing the get_state reply.

    Returns
    -------
    HostInfo
        An instance of HostInfo with attributes populated from the XML element.
    """
    client_state = _get_client_state(client_state)
    host_info_element = client_state.find('host_info')
    if host_info_element is None:
        raise ValueError("<host_info> not found in BOINC reply")
    return HostInfo.from_xml(host_info_element)


def parse_tasks(client_state: ET.Element, project_url: str) -> list[TaskInfo]:
    """
    Parse the tasks from the get_state reply.

    Parameters
    ----------
    client_state : ET.Element
        The XML element representing the get_state reply.
    project_url : str
        The URL of the project for which to parse tasks.

    Returns
    -------
    list of TaskInfo
        A list of TaskInfo objects, each representing a task with its details.
    """
    client_state = _get_client_state(client_state)
    tasks = []
    for task in client_state.findall('result'):
        task_info = TaskInfo.from_xml(task)
        try:
            if task_info.project_url == project_url:
                tasks.append(task_info)
        except AttributeError:  # no project_url attribute in task_info
            pass
    return tasks


def summarise_state(reply: ET.Element) -> dict:
    """
    Collate specific fields from the get_state reply and return them in a structured format.

    Parameters
    ----------
    reply : ET.Element
        The XML element representing the get_state reply.
    
    Returns
    -------
    dict
        A dictionary containing the host information and a list of projects with their associated tasks.
    """
    client_state = _get_client_state(reply)
    summary = {}

    host_info = parse_host_info(client_state)
    summary["host_info"] = host_info

    projects = parse_projects(client_state)
    proj_list = []
    for project in projects:
        tasks = parse_tasks(client_state, project_url=project.master_url)
        proj_list.append({
            "project_info": project,
            "tasks": tasks
        })
    summary["projects"] = proj_list
    return summary



if __name__ == "__main__":
    # Example usage of the parsing functions
    from pathlib import Path

    from . import rpc

    ETX = b"\x03"
    pw = Path("/var/lib/boinc-client/gui_rpc_auth.cfg").read_text().strip()
    rpc_client = rpc.BOINCClient(host="localhost", port=31416, password=pw)
    rpc_client.connect()
    rpc_client.authenticate()
    reply = rpc_client.request("get_state")

    summary = summarise_state(reply)

    # Display the host information
    summary["host_info"].display(logger=logger)

    # Display the project information and associated tasks
    for proj in summary["projects"]:
        proj["project_info"].display(logger=logger)
        for task in proj["tasks"]:
            task.display(logger=logger)
