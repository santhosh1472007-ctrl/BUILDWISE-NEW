import pathlib,re
p=pathlib.Path('seed/s04_nvidia_gpus.py')
text=p.read_text()
names=[m.group(1) for m in re.finditer(r'dict\(name=\"([^\"]+)\"', text)]
print('entries:', len(names))
print('unique_names:', len(set(names)))
print('duplicates:', [n for n in set(names) if names.count(n) > 1])
