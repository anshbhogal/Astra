# ASTRA Secure Execution & Sandbox Architecture Design

## 1. Overview & Architecture

Untrusted repository code and test suites must **never** execute directly inside the ASTRA API backend container or Celery host process. 

The remediation architecture establishes a dedicated, isolated execution plane:

```
FastAPI Gateway / Celery Worker
         │ (Internal Network, Shared Service Token)
         ▼
  sandbox_runner (Dedicated Service)
         │ (Docker Daemon /var/run/docker.sock)
         ▼
  Ephemeral Isolated Container
  ├── User: non-root (1000:1000)
  ├── Network: none (disabled)
  ├── Memory Limit: 512MB (hard limit)
  ├── PID Limit: 128 (anti-forkbomb)
  ├── CPU Quota: 1 Core (1,000,000,000 nano_cpus)
  ├── Filesystem: Read-only Root + Isolated Tmpfs
  └── Capabilities: ALL dropped + no-new-privileges
```

---

## 2. Threat Model

| Threat | Attack Vector | Security Control |
| :--- | :--- | :--- |
| **Host Remote Code Execution (RCE)** | User repository defines custom execution commands with `shell=True` executing on the API container. | Native custom commands eliminated. Commands structured as strict argv lists and executed inside ephemeral disposable containers. |
| **Process Exhaustion (Fork Bomb)** | Malicious test invokes recursive processes (`while True: os.fork()`) starving host OS. | Kernel `pids_limit=128` per container strictly limits thread/process creation. Container is forcibly terminated. |
| **Memory Exhaustion (OOM Bomb)** | Test allocates multi-gigabyte structures (`' ' * (2GB)`) causing host kernel OOM killer to terminate database/backend. | Docker cgroup `mem_limit=512m` and `memswap_limit=512m`. The ephemeral container is OOM-killed in isolation; the host backend remains completely unaffected. |
| **SSRF & Network Traversal** | Malicious code attempts outbound connections to cloud metadata (`169.254.169.254`), database, or internal Redis. | Docker `network_mode: "none"`. All network devices are disabled. Zero ingress and zero egress. |
| **Filesystem Escape & Tampering** | Malicious repository overwrites host application code, steals credentials, or writes cron jobs. | Container root filesystem is mounted `read_only: true`. Host workspace is mounted read-only (`ro`). Only ephemeral memory-backed `tmpfs` mounts (`/tmp` and `/workspace_work`) are writable. |
| **Privilege Escalation** | Attacker leverages setuid binaries or Linux capabilities to escape container. | Container drops all capabilities (`cap_drop: ["ALL"]`), enforces `no-new-privileges: true`, and runs as non-root UID 1000:1000. |
| **Host Port Collisions** | Check-then-bind port allocation races when multiple tests start concurrently. | Docker daemon automatically assigns container ports or test execution runs in self-contained network namespace without host port bindings. |
| **Hanging / Infinite Loop Tests** | Malicious test invokes `while True: pass` or blocked I/O to lock background execution workers. | Hard deadline watchdog terminates container via `SIGKILL` and cleans up container resources. |

---

## 3. Ephemeral Sandbox Specifications

```python
container = client.containers.create(
    image="python:3.11-slim",
    command=command_argv_list,
    network_mode="none",
    mem_limit="512m",
    memswap_limit="512m",
    nano_cpus=1_000_000_000,
    pids_limit=128,
    user="1000:1000",
    read_only=True,
    security_opt=["no-new-privileges:true"],
    cap_drop=["ALL"],
    tmpfs={
        "/tmp": "rw,noexec,nosuid,size=64m",
        "/workspace_work": "rw,size=128m"
    },
    volumes={workspace_path: {"bind": "/workspace", "mode": "ro"}},
    working_dir="/workspace",
    detach=True
)
```
