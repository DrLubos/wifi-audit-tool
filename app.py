import subprocess
import sys
import os

def run_script(script_name, *args):
    venv_path = os.path.join(os.getcwd(), "venv")
    activate_script = os.path.join(venv_path, "bin", "activate")

    if not os.path.exists(activate_script):
        print("Virtual environment not found. Please create one using 'python -m venv venv'.")
        sys.exit(1)

    if script_name not in ["main.py", "report.py"]:
        print(f"Error: Unsupported script '{script_name}'. Please use 'main.py' or 'report.py'.")
        sys.exit(1)

    arg_string = " ".join(args)
    command = f"source {activate_script} && python {script_name} {arg_string}"

    process = subprocess.Popen(command, shell=True, executable="/bin/bash")
    process.communicate()

    if process.returncode != 0:
        print(f"Error: {script_name} encountered an issue.")
        sys.exit(process.returncode)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python3 app.py <script_name> [arguments]")
        sys.exit(1)

    script_name = sys.argv[1]
    script_args = sys.argv[2:]

    run_script(script_name, *script_args)
