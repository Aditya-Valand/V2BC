from app import app

blueprints = sorted([bp for bp in app.blueprints])
print(f'✓ App imported successfully')
print(f'✓ Registered blueprints ({len(blueprints)}): {", ".join(blueprints)}')
