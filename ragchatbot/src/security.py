import time
import logging
from config.config import RATE_LIMIT, TIME_WINDOW, TEMP_BAN_DURATION

# Get logger instance
logger = logging.getLogger("uvicorn.error")

# Stores request history per IP
rate_limit_data = {}

# Tracks temporarily banned IPs
banned_ips = {}

def is_rate_limited(ip: str):
    now = time.time()

    # Check ban list
    if ip in banned_ips:
        ban_expiry = banned_ips[ip]
        if now < ban_expiry:
            logger.warning(
                "IP %s is temporarily banned until %s",
                ip,
                time.ctime(ban_expiry),
                extra={"action": "rate_limit", "status": "banned", "ip": ip}
            )
            return True
        else:
            del banned_ips[ip]

    # Clean up timestamps
    history = rate_limit_data.get(ip, [])
    history = [t for t in history if now - t < float(TIME_WINDOW)]
    history.append(now)
    rate_limit_data[ip] = history

    # Check if limit exceeded
    if len(history) > int(RATE_LIMIT):
        logger.error(
            "DDoS Alert: IP %s made %d requests in %.1f seconds. Banned for %ds",
            ip,
            len(history),
            float(TIME_WINDOW),
            TEMP_BAN_DURATION,
            extra={
                "action": "rate_limit",
                "status": "banned_new",
                "ip": ip,
                "request_count": len(history),
                "window_seconds": float(TIME_WINDOW),
                "ban_duration": TEMP_BAN_DURATION
            }
        )
        banned_ips[ip] = now + TEMP_BAN_DURATION
        return True