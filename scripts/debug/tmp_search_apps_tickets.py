import os
root = r'D:\Ticket-Management-system'
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith('.py'):
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception:
                continue
            if 'apps.tickets' in text:
                print(path)
