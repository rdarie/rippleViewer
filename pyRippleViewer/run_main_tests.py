import os
import signal
import subprocess
import time
import pdb

bashPath = os.path.join('C:\\', 'Program Files', 'Git', 'git-bash.exe')

condaRoot = os.path.join('Anaconda3')
condaBinFolder = os.path.join(condaRoot, 'condabin')
host_cmd = [
    'F:', '&',
    'cd', f'{condaBinFolder}', '&',
    'conda.bat', 'activate', 'rippleViewer']

print(f'{__name__}: pid = {os.getpid()}')
condaRoot = os.path.join('F:\\', 'Anaconda3')
condaBinFolder = os.path.join(condaRoot, 'condabin')
condaExec = os.path.join(condaBinFolder, 'conda.bat')
print('Starting host process...')
flags = (
    subprocess.HIGH_PRIORITY_CLASS
    )
host_cmd = [
    f'{condaExec}', 'activate', 'rippleViewer', '&',
    'python', 'main_host_test.py']
host_process = subprocess.Popen(
    host_cmd, creationflags=flags
    )
print(f'host pid = {host_process.pid}')
print('Sleeping for 10 sec...')
time.sleep(10.)
print('Starting client...')
client_cmd = [
    f'{condaExec}', 'activate', 'rippleViewer', '&',
    'python', 'main_client_test.py']
client_process = subprocess.Popen(
    client_cmd, creationflags=flags
    )
print(f'client pid = {client_process.pid}')
sleepFor = 200
print(f'Sleeping for {sleepFor} sec...')
t_now = time.time()
t_end = t_now + sleepFor

while time.time() < t_end:
    time.sleep(.3)
    print(f'T-{(t_end - time.time()):.3f} sec', end='\r')
