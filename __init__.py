"""Hermes Agent entry point. Hermes supplies the trusted model facade."""


def register(ctx):
    from .formwork.runtime import register_extraction
    register_extraction(ctx)
