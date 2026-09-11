#!/usr/bin/env python3
"""
Launcher Script for Crescendo PRD Defense Interactive Web Testbench.
Featuring Zero-Dependency Hot Reloading for both Frontend and Backend.

- Frontend: Live-reloads the browser automatically when HTML/CSS/JS is edited.
- Backend: Auto-restarts the server process when Python files in src/ or scripts/ are edited.

Usage:
    python run_website.py
    python run_website.py --port 8080
    python run_website.py --no-watch
    python run_website.py --no-browser
"""

import os
import sys
import time
import socket
import argparse
import webbrowser
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def cleanup_lingering_port(port: int):
    """Attempts to free the port on Windows if lingering python processes hold it."""
    if sys.platform == "win32" and is_port_in_use(port):
        print(f"[*] Port {port} is currently busy. Sanitizing lingering instances...")
        try:
            cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"
            output = subprocess.check_output(["powershell", "-Command", cmd], text=True).strip()
            pids = [int(p) for p in output.split() if p.isdigit() and int(p) != os.getpid()]
            for pid in pids:
                subprocess.run(["powershell", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"])
            time.sleep(1.0)
        except Exception as e:
            print(f"[!] Note: Port cleanup note: {e}")


def get_backend_max_mtime():
    """Returns the latest modification timestamp across backend python & config files."""
    watch_dirs = [
        os.path.join(PROJECT_ROOT, "scripts"),
        os.path.join(PROJECT_ROOT, "src", "crs"),
        os.path.join(PROJECT_ROOT, "configs"),
    ]
    mtimes = []
    for d in watch_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".py", ".json")) and not f.startswith("."):
                        try:
                            mtimes.append(os.path.getmtime(os.path.join(root, f)))
                        except OSError:
                            pass
    return max(mtimes) if mtimes else time.time()


def start_server_process(host: str, port: int) -> subprocess.Popen:
    """Starts serve_web_demo.py as a managed child process."""
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["OMP_NUM_THREADS"] = "1"
    env["MPLBACKEND"] = "Agg"
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "scripts", "serve_web_demo.py"),
        "--host", host,
        "--port", str(port)
    ]
    return subprocess.Popen(cmd, env=env)


def main():
    parser = argparse.ArgumentParser(description="Launch Crescendo Defense Web Application with Hot Reloading")
    parser.add_argument("--port", type=int, default=8080, help="Port to host web server on (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    parser.add_argument("--no-watch", action="store_true", help="Disable backend auto-restart file watcher")
    args = parser.parse_args()

    # Step 1: Clean port if occupied
    cleanup_lingering_port(args.port)

    url = f"http://localhost:{args.port}/"
    print("=" * 70)
    print("  CRESCENDO PRD DEFENSE -- WEB TESTBENCH (HOT RELOADING ENABLED)")
    print(f"  URL: {url}")
    print("  • Frontend: Live-reloads instantly upon editing web/ HTML, CSS, JS")
    print("  • Backend:  Auto-restarts server upon editing src/ or scripts/")
    print("=" * 70)

    # Step 2: Delayed browser open
    if not args.no_browser:
        import threading
        def open_browser_delayed():
            time.sleep(2.0)
            print(f"[*] Opening {url} in your default browser...")
            webbrowser.open(url)
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Step 3: Spawn child server
    server_proc = start_server_process(args.host, args.port)
    last_mtime = get_backend_max_mtime()

    print(f"\n[+] Hot reload active. Monitoring for changes... (Press Ctrl+C to stop)")
    sys.stdout.flush()

    try:
        while True:
            time.sleep(1.0)
            # Check if server exited on its own
            if server_proc.poll() is not None:
                print(f"[!] Server process terminated unexpectedly with code {server_proc.returncode}.")
                break

            if not args.no_watch:
                current_mtime = get_backend_max_mtime()
                if current_mtime > last_mtime + 0.5:
                    print("\n[HotReload] Backend code change detected! Restarting server...")
                    server_proc.terminate()
                    try:
                        server_proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        server_proc.kill()

                    cleanup_lingering_port(args.port)
                    server_proc = start_server_process(args.host, args.port)
                    last_mtime = current_mtime
                    print("[+] Server restarted successfully with updated code.\n")

    except KeyboardInterrupt:
        print("\n[*] Stopping server and file watcher...")
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        cleanup_lingering_port(args.port)
        print("[+] Web Testbench stopped cleanly.")


if __name__ == "__main__":
    main()
