import subprocess

command = r"D:\Github\e3nb\scripts\test_bash.sh"

# results = subprocess.run(command, shell=True, capture_output=True)

# print(results.stdout)

# print(subprocess.Popen(command, \
#     shell=True, stdout=subprocess.PIPE).communicate()[0].decode('ascii'))

subprocess.check_output(["echo", "Hello world!"], shell=True)
