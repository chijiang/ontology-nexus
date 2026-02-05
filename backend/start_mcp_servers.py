import subprocess
import time
import sys
import os
import signal

def run_server(module, port, name):
    cmd = [
        "uv", "run", "fastmcp", "run", 
        module, 
        "--transport", "sse", 
        "--port", str(port)
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    # Inject default Neo4j credentials if missing (for local dev)
    if not env.get("NEO4J_URI"):
        env["NEO4J_URI"] = "bolt://localhost:7687"
        env["NEO4J_USERNAME"] = "neo4j"
        env["NEO4J_PASSWORD"] = "password"
        
    print(f"Starting {name} on port {port}...")
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, text=True, env=env)
    return proc

def main():
    query_proc = run_server("app/mcp/query_server.py:mcp", 8001, "Query Server")
    action_proc = run_server("app/mcp/action_server.py:mcp", 8002, "Action Server")

    print("\n✅ Servers are running.")
    print("Query Server: http://localhost:8001/sse")
    print("Action Server: http://localhost:8002/sse")
    print("\nPress Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
            if query_proc.poll() is not None:
                print("Query Server exited unexpectedly.")
                break
            if action_proc.poll() is not None:
                print("Action Server exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping servers...")
    finally:
        query_proc.terminate()
        action_proc.terminate()
        query_proc.wait()
        action_proc.wait()

if __name__ == "__main__":
    main()
