# Shim to expose the top-level `ascending_method` module under the
# `audiometer` package namespace. Tests import `audiometer.ascending_method`
# expecting a module with the same attributes as the top-level module.
try:
    import importlib
    _mod = importlib.import_module('ascending_method')
    # Re-export public attributes for compatibility
    for _name, _val in _mod.__dict__.items():
        if not _name.startswith('__'):
            globals()[_name] = _val
except Exception:
    # Fallback to relative import
    from ..ascending_method import AscendingMethod  # type: ignore
    globals()['AscendingMethod'] = AscendingMethod
