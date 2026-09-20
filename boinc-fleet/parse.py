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

from .logger import get_logger

logger = get_logger("boinc-fleet.parse")


@dataclass
class Coproc:
    """
    A class to represent a coprocessor (e.g., GPU) from the BOINC client.
    """
    name: str             # the name of the GPU or coprocessor
    available_ram: int    # the available RAM on the GPU or coprocessor

    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> "Coproc":
        """
        Create an instance of Coproc from an XML element.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        Coproc
            An instance of Coproc with attributes populated from the XML element.
        """
        return cls(
            name = xml_element.findtext('name', default=''),
            available_ram = int(float(xml_element.findtext('available_ram', default='0')))
        )


@dataclass
class HostInfo:
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
        return cls(
            domain_name = xml_element.findtext('domain_name', default=''),
            ip_addr = xml_element.findtext('ip_addr', default=''),
            p_ncpus = int(xml_element.findtext('p_ncpus', default='0')),
            p_vendor = xml_element.findtext('p_vendor', default=''),
            p_model = xml_element.findtext('p_model', default=''),
            os_version = xml_element.findtext('os_version', default=''),
            coprocs=coprocs
        )

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
class ProjectInfo:
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

    # Task information (optional, may not be present in all replies)
    tasks: list["TaskInfo"] | None = None  # a list of tasks associated with the project, if any

    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> "ProjectInfo":
        """
        Create an instance of ProjectInfo from an XML element, with special handling for optional team fields.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        ProjectInfo
            An instance of ProjectInfo with attributes populated from the XML element.
        """
        return cls(
            project_name = xml_element.findtext('project_name', default=''),
            master_url = xml_element.findtext('master_url', default=''),
            user_name = xml_element.findtext('user_name', default=''),
            user_total_credit = float(xml_element.findtext('user_total_credit', default='0.0')),
            user_expavg_credit = float(xml_element.findtext('user_expavg_credit', default='0.0')),
            hostid = xml_element.findtext('hostid', default=''),
            host_total_credit = float(xml_element.findtext('host_total_credit', default='0.0')),
            host_expavg_credit = float(xml_element.findtext('host_expavg_credit', default='0.0')),
            team_name = xml_element.findtext('team_name', default=None),
            team_total_credit = float(xml_element.findtext('team_total_credit', default='0.0')) \
                if xml_element.find('team_total_credit') is not None else None,
            team_expavg_credit = float(xml_element.findtext('team_expavg_credit', default='0.0')) \
                if xml_element.find('team_expavg_credit') is not None else None,
        )

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
        if self.tasks:
            print(f"Number of Tasks: {len(self.tasks)}")
            for task in self.tasks:
                task.display(logger=logger)


@dataclass
class ActiveTask:
    """
    A class to represent an active task from the BOINC client.
    """
    active_task_state: int       # the current state of the task (e.g., "running", "ready_to_report")
    fraction_done: float         # the fraction of the task that is completed (0.0 to 1.0)
    elapsed_time: float          # the elapsed time for the task in seconds

    @classmethod    
    def from_xml(cls, xml_element: ET.Element) -> "ActiveTask":
        """
        Create an instance of ActiveTask from an XML element.

        Parameters
        ----------
        xml_element : ET.Element
            The XML element to parse.

        Returns
        -------
        ActiveTask
            An instance of ActiveTask with attributes populated from the XML element.
        """
        return cls(
            active_task_state = int(xml_element.findtext('active_task_state', default='0')),
            fraction_done = float(xml_element.findtext('fraction_done', default='0.0')),
            elapsed_time = float(xml_element.findtext('elapsed_time', default='0.0'))
        ) 

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
class TaskInfo:
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
        return cls(
            name = xml_element.findtext('name', default=''),
            wu_name = xml_element.findtext('wu_name', default=''),
            project_url = xml_element.findtext('project_url', default=''),
            estimated_cpu_time_remaining = float(xml_element.findtext('estimated_cpu_time_remaining', default='0.0')),
            report_deadline = float(xml_element.findtext('report_deadline', default='0.0')),
            active_task = active_task
        )

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
        project_info = ProjectInfo.from_xml(project)
        project_info.tasks = parse_tasks(client_state, project_url=project_info.master_url)
        projects.append(project_info)
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
        if task_info.project_url == project_url:
            tasks.append(task_info)
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
    return {
        "host_info": parse_host_info(client_state),
        "projects": parse_projects(client_state)
    }


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
        proj.display(logger=logger)
