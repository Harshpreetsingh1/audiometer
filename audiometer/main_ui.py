# Shim to expose the top-level `main_ui` module under the package
# `audiometer.main_ui`. Tests expect to be able to patch attributes on the
# module (e.g., `audiometer.main_ui.AscendingMethod`), so re-export public
# names from the top-level module.
try:
    import importlib
    _mod = importlib.import_module('main_ui')
    for _name, _val in _mod.__dict__.items():
        if not _name.startswith('__'):
            globals()[_name] = _val
except Exception:
    # Fallback to relative import
    from ..main_ui import AudiometerUI, main  # type: ignore
    globals()['AudiometerUI'] = AudiometerUI
    globals()['main'] = main
