"""
TSW (Troubleshooting Wizard) Query Modules

This package contains modular query classes for TSW diagnostic tools.
Each module corresponds to a specific TSW workflow:

- UDF Analysis: User-Defined Functions diagnostics
- Query Compilation: Compilation performance analysis
- Iceberg Tables: Iceberg table diagnostics
- Query Locks: Transaction lock analysis
- Incident Errors: Error tracking and incident mapping
- User Authentication: SAML/OAUTH authentication diagnostics
- RBAC: Role-Based Access Control analysis
"""

from app.queries.tsw.auth_queries import AuthQueries
from app.queries.tsw.compilation_queries import CompilationQueries
from app.queries.tsw.iceberg_queries import IcebergQueries
from app.queries.tsw.incident_queries import IncidentQueries
from app.queries.tsw.locks_queries import LocksQueries
from app.queries.tsw.rbac_queries import RbacQueries
from app.queries.tsw.udf_queries import UdfQueries

__all__ = [
    "UdfQueries",
    "CompilationQueries",
    "IncidentQueries",
    "IcebergQueries",
    "LocksQueries",
    "AuthQueries",
    "RbacQueries",
]
