"""Asynchronous persistence adapter foundation."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for future PaperTrading persistence models."""
