import os
import subprocess
from pathlib import Path
import sys

# 1. Get full path to the root directory.
directory = Path(__file__).parent

print(f'1. Current root directory: {directory}\n')


# 2. Search for python /Scripts/ directory.
for path in os.environ['PATH'].split(';'):
    scripts_directory = Path(path)
    # Full path should contain 'python' and 'scripts' substrings.
    if 'python' in path.lower() and 'scripts' in path.lower():
        # In the found directory, there should be 'pip.exe' file. Otherwise, it's a wrong directory.
        if any(item.name == 'pip.exe' for item in scripts_directory.iterdir()):
            print(f'2. Python/Scripts directory: {scripts_directory}\n')
            break
else:
    print('2. ERROR: Python/Scripts directory was not found.')
    sys.exit(1)


# 3. Create the proper .bat file in the /Scripts/ directory.
with open(f'{scripts_directory / 'CCL!.bat'}', 'w', encoding='utf-8') as bat:
    bat.write('@echo off\n')
    bat.write(f'python "{directory / 'interpreter/main.py'}" %*')

print(f'3. CCL!.bat was successfully created.\n')


# 4. Install dependencies.
dependencies_check = input('Do you want to install dependencies? (y/n): ').strip().lower()
if dependencies_check not in ('y', 'yes'):
    print('\n4. Dependencies will not be installed.\n')
else:
    print()
    subprocess.run(['pip', 'install', '-r', 'requirements.txt'])
    print(f'\n4. Dependencies were installed.\n')

print('Installation is done!')
print('USAGE: CCL! <filepath> [-args...]\n')
