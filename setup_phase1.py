import os

folders = [
    'input',
    'output',
    'logs',
    'reports',
    'agents',
    'services',
    'models',
    'utils',
    'assets'
]

base_dir = r"c:\Users\Admin\.antigravity\real_estate_agent"

for folder in folders:
    os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
    with open(os.path.join(base_dir, folder, '__init__.py'), 'w') as f:
        pass

print("Folders created successfully.")
