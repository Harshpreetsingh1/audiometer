from types import SimpleNamespace
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

called={'press':False,'release':False}

def on_press_key(name, cb, suppress=True):
    print('on_press_key called', name, 'suppress=', suppress)
    called['press']=True
    return 'press_'+name

def on_release_key(name, cb, suppress=True):
    print('on_release_key called', name, 'suppress=', suppress)
    called['release']=True
    return 'release_'+name

mock = SimpleNamespace(on_press_key=on_press_key, on_release_key=on_release_key, unhook=lambda h: None)

sys.modules['keyboard'] = mock

from audiometer.responder import Responder
r = Responder(1.0)
print('called dict after init:', called)
print('handlers:', getattr(r, '_handlers', None))
import inspect
print('\nResponder class source:\n')
print(inspect.getsource(Responder))
print('\nResponder instance __dict__:\n', r.__dict__)
print('\nAttempting to call _register_media_key_handlers() explicitly...')
try:
    r._register_media_key_handlers()
    print('called dict after explicit register:', called)
    print('handlers after explicit register:', getattr(r, '_handlers', None))
except Exception as e:
    print('explicit register raised', e)
print('\nResponder runtime type info:')
print('type(r):', type(r))
print('r.__class__ module:', r.__class__.__module__)
print('r.__class__ dict keys:', [k for k in r.__class__.__dict__.keys() if not k.startswith('__')][:40])
print('dir(r) includes _register_media_key_handlers?:', '_register_media_key_handlers' in dir(r))
