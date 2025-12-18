from types import SimpleNamespace
import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

callbacks = {}

def on_press_key(name, cb, suppress=True):
    print('on_press_key called', name)
    callbacks['press_'+name] = cb
    return 'id'

def on_release_key(name, cb, suppress=True):
    print('on_release_key called', name)
    callbacks['release_'+name] = cb
    return 'id'

mock_k = SimpleNamespace(on_press_key=on_press_key, on_release_key=on_release_key, unhook=lambda h: None)

print('Injecting mock keyboard into sys.modules')
sys.modules['keyboard'] = mock_k

from audiometer.responder import Responder
r = Responder(1.0)
import inspect
import importlib
mod = importlib.import_module('audiometer.responder')
print('Responder class module:', mod)
print('Responder file:', getattr(mod, '__file__', 'n/a'))
import inspect
src = inspect.getsource(mod)
print('Responder source (first 1200 chars):\n', src[:1200])
print('Responder class attrs:', [a for a in dir(r) if not a.startswith('_')])
print('Registered callbacks:', list(callbacks.keys()))
print('Has _handlers attribute?:', hasattr(r, '_handlers'))
print('suppress_supported attribute?', getattr(r, '_suppress_supported', 'n/a'))
print('Instance __dict__:', r.__dict__)

# Try invoking press handler if present
if 'press_volume up' in callbacks:
    callbacks['press_volume up'](None)
    print('After press, click_down:', r.click_down())
else:
    print('press_volume up not registered')
