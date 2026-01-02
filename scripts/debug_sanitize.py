import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audiometer.controller import Controller
ctrl = Controller()
inputs = ["👴🔊","'; DROP TABLE patients; --","A"*10000,"\x00\x01\x02","../../../etc/passwd","CON","PRN","AUX","NUL","COM1","LPT1","file.txt","file.csv","file.pdf","/","\\",":","*","?","<>|","  ","","\n\r\t"]
failures = []
creation_failures = []
for s in inputs:
    try:
        # Create controller with subject_name to see if it raises
        c = Controller(subject_name=s)
        out = c._sanitize_folder_name(s)
        # Close any opened files to avoid locking
        if hasattr(c, 'csvfile') and c.csvfile:
            try:
                c.csvfile.close()
            except:
                pass
    except Exception as e:
        creation_failures.append((s, str(e)))
        out = f"!EXCEPTION: {e}"
    print(repr(s)[:50].ljust(20), ' -> ', repr(out)[:200])

print('\nCreation Failures:')
for f in creation_failures:
    print(' -', f)
print('Total creation failures:', len(creation_failures))


