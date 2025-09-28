"""
Database views module.

This module contains all SQL views organized by category:
- active_records: Views for filtering non-soft-deleted records
- auth: Authentication and security related views
- community: Community management views
"""

from src.database.views.active_records import ACTIVE_VIEWS_SQL, DROP_ACTIVE_VIEWS_SQL
from src.database.views.auth_views import AUTH_VIEWS_SQL, DROP_AUTH_VIEWS_SQL
from src.database.views.community_views import COMMUNITY_VIEWS_SQL, DROP_COMMUNITY_VIEWS_SQL

# Combine all views
ALL_VIEWS_SQL = {
    **ACTIVE_VIEWS_SQL,
    **AUTH_VIEWS_SQL,
    **COMMUNITY_VIEWS_SQL
}

# Combine all drop statements
ALL_DROP_VIEWS_SQL = [
    *DROP_ACTIVE_VIEWS_SQL,
    *DROP_AUTH_VIEWS_SQL,
    *DROP_COMMUNITY_VIEWS_SQL
]

__all__ = [
    'ALL_VIEWS_SQL',
    'ALL_DROP_VIEWS_SQL',
    'ACTIVE_VIEWS_SQL',
    'AUTH_VIEWS_SQL', 
    'COMMUNITY_VIEWS_SQL',
    'DROP_ACTIVE_VIEWS_SQL',
    'DROP_AUTH_VIEWS_SQL',
    'DROP_COMMUNITY_VIEWS_SQL'
]
