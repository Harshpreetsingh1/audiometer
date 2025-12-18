import os
p = 'audiometer/__pycache__/responder.cpython-312.pyc'
print('exists', os.path.exists(p))
if os.path.exists(p):
    print('size', os.path.getsize(p))
    with open(p, 'rb') as f:
        data = f.read(64)
    print('first bytes', data)
