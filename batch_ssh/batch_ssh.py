#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import subprocess
import configparser
import textwrap
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# 基础信息
script_path = Path(sys.argv[0]).resolve()

@dataclass(frozen=True)
class Host:
    name: str
    host: str
    user: str
    port: str
    password: str

@dataclass(frozen=True)
class Result:
    output: str
    returncode: int | None

def load_config(path):
    if not os.path.exists(path):
        print(f"error: config path '{path}' does not exist", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path):
        print(f"error: config path '{path}' is not a file", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    try:
        config.read(path, encoding="utf-8")
        hosts = []
        for section in config.sections():
            host_entry = Host(
                name=section,
                host=config.get(section, "host", fallback=section),
                user=config.get(section, "user", fallback=""),
                port=config.get(section, "port", fallback="22"),
                password=config.get(section, "password", fallback="")
            )
            hosts.append(host_entry)
        return hosts
    except Exception as e:
        print(f"error: failed to parse config file. exception: {e}", file=sys.stderr)
        sys.exit(1)

def ssh(host: Host, command: str, timeout: int) -> Result:
    ssh_cmd = [
        "ssh",
        "-p", host.port,
        "-o", f"ConnectTimeout={timeout}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{host.user}@{host.host}" if host.user else f"{host.host}", 
        command
    ]

    try:
        result = subprocess.run(
            ssh_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            errors="ignore"
        )
        return Result(
            output=result.stdout,
            returncode=result.returncode
        )
    except Exception as e:
        return Result(
            output=str(e),
            returncode=None
        )

def main():
    print(f"cmd: {script_path.name} {' '.join(sys.argv[1:])}")
    print(f"exe: {script_path}")
    print(f"cwd: {os.getcwd()}\n")
    
    default_config_path = script_path.parent / "config.ini"
    parser = argparse.ArgumentParser(description="ssh probe tool to execute commands on multiple remote hosts")
    parser.add_argument("command", nargs="+", help="command to be executed on remote hosts")
    parser.add_argument("-c", "--config", default=default_config_path, help=f"path to the config file (default: {default_config_path})")
    parser.add_argument("-j", "--jobs", type=int, default=16, help="number of concurrent jobs (default: 16)")
    parser.add_argument("-t", "--timeout", type=int, default=5, help="ssh timeout in seconds (default: 5)")
    args = parser.parse_args()

    hosts = load_config(args.config)
    if not hosts:
        print(f"error: no valid hosts found in config file '{args.config}'", file=sys.stderr)
        sys.exit(1) 
        
    command = " ".join(args.command)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        res = []
        for host in hosts:
            future = executor.submit(ssh, host, command, args.timeout)
            res.append([host, future])
        
        max_prefix_len = 0
        for entry in res:
            host = entry[0]
            prefix = f"{host.name} ({host.host})" if host.name != host.host else host.name
            max_prefix_len = max(max_prefix_len, len(prefix))
            entry.append(prefix)

        for host, future, prefix in res:
            future_res = future.result()
            output = future_res.output.strip()
            if future_res.returncode is None:
                assert("\n" not in output)
                output = f"exception: {output}"
                suffix = "---"
            else:
                suffix = future_res.returncode
            
            output_lines = output.splitlines(keepends=True)
            # 处理缩进
            output = output_lines[0] + "".join(textwrap.indent("".join(output_lines[1:]), " " * (max_prefix_len + 8)))
            print(f"[{prefix:<{max_prefix_len}}][{suffix:>3}] {output}")
            
if __name__ == "__main__":
    main()
