# models/__init__.py — re-exports all models from domain submodules

from models.organization import Departement, TypeCourrierSortant, StatutCourrier
from models.user import User
from models.courrier import Courrier, CourrierAttachment, CourrierModification, CourrierForward, CourrierComment, CourrierSignature
from models.tag import Tag, CourrierTag
from models.rbac import Role, RolePermission
from models.system import ParametresSysteme, EmailTemplate, IPBlock, IPWhitelist
from models.notification import Notification
from models.log import LogActivite


def init_default_data():
    """Initialise toutes les données par défaut"""
    StatutCourrier.init_default_statuts()
    Role.init_default_roles()
    RolePermission.init_default_permissions()
    Departement.init_default_departments()
    EmailTemplate.init_default_templates()


__all__ = [
    'Departement', 'TypeCourrierSortant', 'StatutCourrier',
    'User',
    'Courrier', 'CourrierAttachment', 'CourrierModification', 'CourrierForward', 'CourrierComment', 'CourrierSignature',
    'Tag', 'CourrierTag',
    'Role', 'RolePermission',
    'ParametresSysteme', 'EmailTemplate', 'IPBlock', 'IPWhitelist',
    'Notification',
    'LogActivite',
    'init_default_data',
]
