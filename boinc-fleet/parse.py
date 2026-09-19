"""
A module to parse a XML `get_state` reply and return clean Python objects.    

The objects returned are dataclasses that can be used to access the data in a structured way. They do not encompass
all possible XML fields returned by the BOINC client, but only the most relevant ones. The dataclasses can be extended
to include additional fields as needed.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass


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
        Create an instance of the class from an XML element.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        An instance of the class with attributes populated from the XML element.
        """
        kwargs = {child.tag: child.text for child in xml_element}
        return cls(**kwargs)

    def __repr__(self):
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
    def from_xml(cls, xml_element: ET.Element):
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
        try:
            coprocs = [Coproc.from_xml(c) for c in xml_element.findall('coproc')]
        except AttributeError as e:
            raise ValueError(f"Error parsing <coproc> elements: {e}."
                             f"\nXML: {ET.tostring(xml_element, encoding='unicode')}")
        kwargs = {child.tag: child.text for child in xml_element if child.tag != 'coprocs'}
        return cls(coprocs=coprocs, **kwargs)


@dataclass
class ProjectInfo(XMLStructure):
    """
    A class to represent the project information from the BOINC client.
    """
    project_name: str            # the name of the project
    master_url: str              # the URL of the project's master server
    user_name: str               # the name of the user associated with the project
    team_name: str               # the name of the team associated with the project
    hostid: str                  # the unique identifier for the host in the project
    user_total_credit: float     # the total credit earned by the user in the project
    user_expavg_credit: float    # the exponentially averaged credit for the user in the project
    team_total_credit: float     # the total credit earned by the team in the project
    team_expavg_credit: float    # the exponentially averaged credit for the team in the project
    host_total_credit: float     # the total credit earned by the host in the project
    host_expavg_credit: float    # the exponentially averaged credit for the host in the project


@dataclass
class ActiveTask(XMLStructure):
    """
    A class to represent an active task from the BOINC client.
    """
    project_url: str             # the URL of the project associated with the task
    active_task_state: int       # the current state of the task (e.g., "running", "ready_to_report")
    fraction_done: float         # the fraction of the task that is completed (0.0 to 1.0)
    elapsed_time: float          # the elapsed time for the task in seconds


@dataclass
class TaskInfo(XMLStructure):
    """
    A class to represent the task information from the BOINC client.
    """
    name: str                              # the name of the task
    wu_name: str                           # the work unit name associated with the task
    project_url: str                       # the URL of the project associated with the task
    fraction_done: float                   # the fraction of the task that is completed (0.0 to 1.0)
    estimated_cpu_time_remaining: float    # the estimated runtime for the task in seconds
    report_deadline: float                 # the report deadline for the task
    active_task: ActiveTask | None         # the active task details, if any

    @classmethod
    def from_xml(cls, xml_element: ET.Element):
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
        kwargs = {child.tag: child.text for child in xml_element if child.tag != 'active_task'}
        return cls(active_task=active_task, **kwargs)


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
    host_info_element = client_state.find('host_info')
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
    list of dict
        A list of dictionaries, each representing a task with its details.
    """
    tasks = []
    for task in client_state.findall('task'):
        task_info = TaskInfo.from_xml(task)
        if task_info.project_url == project_url:
            tasks.append(task_info)
    return tasks


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

    host_info = parse_host_info(reply)
    print(f"Host Info: {host_info}")
    projects = parse_projects(reply)
    print(f"Projects: {projects}")
    tasks = parse_tasks(reply, project_url=projects[0].master_url if projects else "")
    print(f"Tasks: {tasks}")
