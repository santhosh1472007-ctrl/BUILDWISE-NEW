from pathlib import Path
p = Path('static/style.css')
text = p.read_text(encoding='utf-8', errors='ignore')
marker = '.auth-links a:hover {'
i = text.find(marker)
if i == -1:
    raise SystemExit('marker not found')
j = text.find('}', i)
if j == -1:
    raise SystemExit('closing brace not found')
p.write_text(text[:j+1].rstrip() + '\n', encoding='utf-8')
print('rewritten', p)
