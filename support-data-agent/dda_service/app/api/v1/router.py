"""
Main API v1 router that includes all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import accounts, cases, jira, queries, tsw, warehouses

# Create API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    queries.router,
    prefix="/queries",
    tags=["Queries"],
)

api_router.include_router(
    accounts.router,
    tags=["Accounts"],
)

api_router.include_router(
    warehouses.router,
    tags=["Warehouses"],
)

api_router.include_router(
    tsw.router,
    prefix="/tsw",
    tags=["TSW"],
)

api_router.include_router(
    cases.router,
    prefix="/cases",
    tags=["Cases"],
)

api_router.include_router(
    jira.router,
    prefix="/jira",
    tags=["JIRA"],
)

# TODO: Add other routers as they are implemented
# api_router.include_router(snowpipes.router, prefix="/snowpipes", tags=["Snowpipes"])
# api_router.include_router(parameters.router, prefix="/parameters", tags=["Parameters"])
# api_router.include_router(search.router, prefix="/search", tags=["Search"])
# api_router.include_router(landing.router, prefix="/landing", tags=["Landing"])
