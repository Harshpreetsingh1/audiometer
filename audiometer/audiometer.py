"""Convenience module to expose core submodules for legacy imports.

Some tests import `audiometer.audiometer` to get access to `controller` and
other helper modules — provide a small shim that re-exports common modules.
"""
from . import controller, config, responder, tone_generator
# Re-export controller.config for tests that import audiometer.audiometer.controller
