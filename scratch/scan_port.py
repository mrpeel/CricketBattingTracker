#!/usr/bin/env python3
import socket
import concurrent.futures
import sys

target = "192.168.1.73"

def check_port(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            res = s.connect_ex((target, port))
            if res == 0:
                return port
    except Exception:
        pass
    return None

def main():
    print(f"Scanning {target} for open Wear OS wireless debugging ports...")
    
    # Try 5555 first
    if check_port(5555):
        print(f"🎯 Found open port: 5555")
        sys.exit(0)
        
    ports = range(30000, 50000)
    with concurrent.futures.ThreadPoolExecutor(max_workers=500) as executor:
        results = executor.map(check_port, ports)
        for port in results:
            if port is not None:
                print(f"🎯 Found open port: {port}")
                sys.exit(0)
    print("❌ No open port found in range 30000-50000 or 5555")

if __name__ == "__main__":
    main()
