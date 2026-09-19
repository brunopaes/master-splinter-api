"""FastAPI app: wires the routers, CORS and error handling together.

Run with ``uvicorn api.main:app --reload``.

"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.handlers import altitude, profile
from api.utils.errors import register_exception_handlers
from master_splinter import __version__

# uvicorn configures its own "uvicorn"/"uvicorn.access" loggers but leaves
# the root logger alone, so without this the module-level loggers below
# would be silently dropped by the default WARNING-only last-resort handler.
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)

app = FastAPI(
    title="master-splinter API",
    version=__version__,
    description=(
        "Wraps the profile and altitude analysers for the master-splinter-web "
        "front end. Not dive planning software - see the master-splinter "
        "package docstring."
    ),
)

# The website is served from a different origin (static hosting). Tighten
# allow_origins to the deployed site's origin before running this in
# production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(profile.router)
app.include_router(altitude.router)
