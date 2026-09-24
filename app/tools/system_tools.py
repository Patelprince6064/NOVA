"""System information tools — read-only, safe."""
import logging
import platform
import shutil
import socket
import datetime
from typing import Tuple

logger = logging.getLogger(__name__)


def _safe_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        return None


def get_system_info() -> Tuple[bool, str]:
    try:
        info = []
        info.append(f"Computer: {platform.node()}")
        info.append(f"System: {platform.system()} {platform.release()} {platform.version()[:40]}")
        info.append(f"Processor: {platform.processor() or platform.machine()}")
        info.append(f"Python: {platform.python_version()}")
        psutil = _safe_psutil()
        if psutil:
            mem = psutil.virtual_memory()
            info.append(f"Memory: {mem.total // (1024**3)} GB total, {mem.available // (1024**3)} GB available ({mem.percent}% used)")
        # GPU placeholder
        info.append(f"Architecture: {platform.architecture()[0]}")
        return True, " | ".join(info)
    except Exception as exc:
        logger.exception("system_info failed: %s", exc)
        return False, "I couldn't get system information."


def get_cpu_info() -> Tuple[bool, str]:
    try:
        psutil = _safe_psutil()
        if psutil:
            cpu = psutil.cpu_percent(interval=0.5)
            cores = psutil.cpu_count(logical=False) or 1
            logical = psutil.cpu_count(logical=True) or cores
            freq = psutil.cpu_freq()
            freq_str = f" {freq.current:.0f} MHz" if freq else ""
            return True, f"CPU usage: {cpu:.1f}% | Cores: {cores} physical, {logical} logical{freq_str}"
        # Fallback without psutil
        return True, f"CPU: {platform.processor() or 'Unknown'} | Cores: {platform.machine()}"
    except Exception as exc:
        logger.exception("cpu_info failed: %s", exc)
        return False, "I couldn't get CPU information."


def get_memory_info() -> Tuple[bool, str]:
    try:
        psutil = _safe_psutil()
        if psutil:
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            avail_gb = mem.available / (1024**3)
            used_gb = mem.used / (1024**3)
            return True, f"RAM: {used_gb:.1f} GB used of {total_gb:.1f} GB ({mem.percent:.0f}% used), {avail_gb:.1f} GB available"
        return True, "Memory information unavailable (install psutil)."
    except Exception as exc:
        logger.exception("memory_info failed: %s", exc)
        return False, "I couldn't get memory information."


def get_storage_info() -> Tuple[bool, str]:
    try:
        psutil = _safe_psutil()
        if psutil:
            parts = psutil.disk_partitions(all=False)
            msgs = []
            for p in parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    total = usage.total // (1024**3)
                    free = usage.free // (1024**3)
                    pct = usage.percent
                    msgs.append(f"{p.device} ({p.mountpoint}): {free} GB free of {total} GB ({pct}% used)")
                except Exception:
                    continue
            if msgs:
                return True, " | ".join(msgs[:4])
        # Fallback: check C:
        total, used, free = shutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
        return True, f"Drive C: {free//(1024**3)} GB free of {total//(1024**3)} GB"
    except Exception as exc:
        logger.exception("storage_info failed: %s", exc)
        return False, "I couldn't get storage information."


def get_battery_info() -> Tuple[bool, str]:
    try:
        psutil = _safe_psutil()
        if psutil:
            batt = psutil.sensors_battery()
            if batt is None:
                return True, "Battery information not available on this device."
            pct = batt.percent
            plugged = "plugged in" if batt.power_plugged else "on battery"
            secs = batt.secsleft
            if secs != -1 and secs != -2:
                hrs = secs // 3600
                mins = (secs % 3600) // 60
                return True, f"Battery: {pct:.0f}% ({plugged}), {hrs}h {mins}m remaining"
            return True, f"Battery: {pct:.0f}% ({plugged})"
        return True, "Battery information unavailable (install psutil)."
    except Exception as exc:
        logger.exception("battery_info failed: %s", exc)
        return False, "I couldn't get battery information."


def get_network_info() -> Tuple[bool, str]:
    try:
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "unknown"
        psutil = _safe_psutil()
        wifi_info = ""
        internet = "unknown"
        # Simple internet check via socket to 8.8.8.8:53
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
            s.close()
            internet = "connected"
        except Exception:
            internet = "not connected"

        if psutil:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            active = [name for name, st in stats.items() if st.isup]
            wifi_info = f" Active: {', '.join(active[:3])}" if active else ""
            # Try to find Wi-Fi
            for name in active:
                if "wi-fi" in name.lower() or "wlan" in name.lower() or "wireless" in name.lower():
                    wifi_info = f" Wi-Fi is on ({name})." + wifi_info
                    break

        return True, f"Host: {hostname} | IP: {ip} | Internet: {internet}.{wifi_info}"
    except Exception as exc:
        logger.exception("network_info failed: %s", exc)
        return False, "I couldn't get network information."


def get_process_info(query: str = "") -> Tuple[bool, str]:
    try:
        psutil = _safe_psutil()
        if not psutil:
            return True, "Process information requires psutil. Install with pip install psutil."
        # If query like "most cpu" -> top process
        q = (query or "").lower()
        if "cpu" in q or "most" in q:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    # Need second sample for cpu_percent
                    procs.append(p)
                except Exception:
                    continue
            # Sample cpu
            for p in procs:
                try:
                    p.cpu_percent(interval=0.1)
                except Exception:
                    pass
            import time
            time.sleep(0.2)
            top = sorted(procs, key=lambda x: x.info.get("cpu_percent") or 0, reverse=True)[:5]
            lines = []
            for p in top:
                try:
                    lines.append(f"{p.info['name']} ({p.info['pid']}): {p.info.get('cpu_percent',0):.1f}%")
                except Exception:
                    continue
            return True, "Top CPU: " + " | ".join(lines) if lines else "No process data."
        if "memory" in q or "ram" in q:
            procs = sorted(psutil.process_iter(["pid", "name", "memory_percent"]), key=lambda x: x.info.get("memory_percent") or 0, reverse=True)
            top = list(procs)[:5]
            lines = [f"{p.info['name']} ({p.info['pid']}): {p.info.get('memory_percent',0):.1f}%" for p in top]
            return True, "Top Memory: " + " | ".join(lines)
        if query and len(query) > 2:
            # Is specific app running?
            for p in psutil.process_iter(["name"]):
                try:
                    if query.lower() in p.info["name"].lower():
                        return True, f"{query} is running (found {p.info['name']})."
                except Exception:
                    continue
            return True, f"{query} doesn't appear to be running."
        # Generic list
        count = len(list(psutil.process_iter()))
        return True, f"{count} processes running. Top CPU: " + get_process_info("most cpu")[1][:120]
    except Exception as exc:
        logger.exception("process_info failed: %s", exc)
        return False, "I couldn't get process information."


def get_date_time() -> Tuple[bool, str]:
    try:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        return True, f"Today is {date_str}, time is {time_str}."
    except Exception as exc:
        logger.exception("get_date_time failed: %s", exc)
        return False, "I couldn't get the date and time."


def calculate_expression(expr: str) -> Tuple[bool, str]:
    """Safe math parser — no eval."""
    try:
        import re
        import math
        # Allow only numbers, operators, parentheses, dot, percent
        expr_clean = expr.strip().lower()
        # Replace words
        repl = {
            "plus": "+", "minus": "-", "times": "*", "x": "*", "multiplied by": "*",
            "divided by": "/", "over": "/", "percent of": "*0.01*",
            "percent": "*0.01",
        }
        # Handle percent of specially
        expr_clean = expr_clean.replace("percent of", "*0.01*")
        for k, v in repl.items():
            expr_clean = expr_clean.replace(k, v)
        # Remove allowed words like calculate, what is
        expr_clean = re.sub(r"(calculate|what is|what's|equals?|is)", "", expr_clean)
        expr_clean = expr_clean.strip()
        # Only allow safe chars
        if not re.match(r"^[\d\.\+\-\*\/\%\(\)\s]+$", expr_clean):
            return False, "I couldn't calculate that. Use numbers and + - * / % ( )."
        # No **, no //
        if "**" in expr_clean or "//" in expr_clean:
            return False, "I can't calculate that expression."
        # Evaluate with safe ast
        import ast

        node = ast.parse(expr_clean, mode="eval")

        allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Load)
        for n in ast.walk(node):
            if not isinstance(n, allowed):
                return False, "I can't calculate that."

        result = eval(compile(node, "<calc>", "eval"), {"__builtins__": {}}, {})
        # Format
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return True, f"Result is {result}."
    except ZeroDivisionError:
        return False, "Division by zero."
    except Exception as exc:
        logger.debug("calculate failed %r: %s", expr, exc)
        return False, "I couldn't calculate that."
