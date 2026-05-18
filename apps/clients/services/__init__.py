"""Services package for the Clients CRM module.

Exposes service modules for client management, projects, communications,
portals, and profitability analysis.
"""

from .clients import ClientService
from .communications import CommunicationService
from .portals import PortalService
from .profitability import ProfitabilityService
from .projects import ProjectService

__all__ = [
    "ClientService",
    "ProjectService",
    "CommunicationService",
    "PortalService",
    "ProfitabilityService",
]
