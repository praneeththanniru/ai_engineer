import subprocess

def run_shell(cmd):
    try:
        print(f"[shell] $ {cmd}")
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(r.stdout)
        if r.stderr:
            print(r.stderr)
    except Exception as e:
        print("Shell Error:", e)
