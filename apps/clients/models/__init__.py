"""Models package for the Clients CRM module.

Exports all models for the clients app: Client, ClientContact, Project,
ProjectMilestone, CommunicationLog, ClientPortal, ClientProfitability.
"""

from apps.clients.models.client import Client, ClientContact
from apps.clients.models.communication import CommunicationLog
from apps.clients.models.portal import ClientPortal
from apps.clients.models.profitability import ClientProfitability
from apps.clients.models.project import Project, ProjectMilestone

__all__ = [
    "Client",
    "ClientContact",
    "ClientPortal",
    "ClientProfitability",
    "CommunicationLog",
    "Project",
    "ProjectMilestone",
]
