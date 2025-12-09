#!/usr/bin/env python3
"""
Master script to run all Dialed services together.

This will start:
1. FastAPI backend (port 8000)
2. Gaze tracking service
3. Label service (keyboard shortcuts)

Press Ctrl+C to stop all services.
"""

import subprocess
import sys
import time
import signal
import os

# Store process handles
processes = []


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down all services...")

    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("All services stopped.")
    sys.exit(0)


def main():
    """Start all services."""
    global processes

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("DIALED - Study Session Distraction Classifier")
    print("=" * 60)
    print("\nStarting all services...\n")

    # Get python executable from virtual environment if available
    python_exe = sys.executable

    # 1. Start FastAPI backend
    print("[1/3] Starting FastAPI backend (port 8000)...")
    backend_proc = subprocess.Popen(
        [python_exe, "backend/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(backend_proc)
    time.sleep(2)  # Give backend time to start

    # 2. Start gaze service
    print("[2/3] Starting gaze tracking service...")
    gaze_proc = subprocess.Popen(
        [python_exe, "services/gaze_service.py", "--fps", "8"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(gaze_proc)
    time.sleep(1)

    # 3. Start label service
    print("[3/3] Starting label service (keyboard shortcuts)...")
    label_proc = subprocess.Popen(
        [python_exe, "services/label_service.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(label_proc)
    time.sleep(1)

    print("\n" + "=" * 60)
    print("All services started successfully!")
    print("=" * 60)
    print("\nServices running:")
    print("  - Backend API:        http://localhost:8000")
    print("  - API Docs:           http://localhost:8000/docs")
    print("  - Gaze Tracking:      Active (8 fps)")
    print("  - Label Shortcuts:    Ctrl+Shift+D/F")
    print("\nChrome Extension:")
    print("  - Install from:       chrome-extension/")
    print("  - Instructions:       chrome-extension/README.md")
    print("\nPress Ctrl+C to stop all services.")
    print("=" * 60)
    print("\nService logs:\n")

    # Stream output from all processes
    try:
        while True:
            # Check if any process died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"\nWARNING: Process {i+1} exited unexpectedly!")
                    # Read remaining output
                    output = proc.stdout.read()
                    if output:
                        print(output)

            time.sleep(0.5)

    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
