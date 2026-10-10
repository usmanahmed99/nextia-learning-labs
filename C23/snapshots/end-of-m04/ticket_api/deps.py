"""Dependencies that many routes share."""

from typing import Annotated

from fastapi import Depends, Request

from ticket_api.db import Database, DatabaseUnavailable


def get_db(request: Request) -> Database:
    db = request.app.state.db
    if db is None:
        raise DatabaseUnavailable("DATABASE_URL is not set")
    return db


DB = Annotated[Database, Depends(get_db)]
