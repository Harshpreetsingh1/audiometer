import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from audiometer.responder import Responder
    print('Imported Responder')
    try:
        r = Responder(1.0)
        print('Created Responder instance')
        print('Instance dict:', r.__dict__)
    except Exception as e:
        print('Exception during Responder init:', e)
except Exception as e:
    print('Failed to import responder:', e)
    import traceback
    traceback.print_exc()
