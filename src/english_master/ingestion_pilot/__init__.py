"""Offline, authorization-bound real-record pilot for approved Tatoeba text."""

from .service import prepare, run, verify

__all__ = ["prepare", "run", "verify"]
