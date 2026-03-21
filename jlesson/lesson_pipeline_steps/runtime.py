"""Runtime accessors for the lesson pipeline facade."""

from __future__ import annotations

from importlib import import_module


def lesson_pipeline_module():
    return import_module("jlesson.lesson_pipeline")