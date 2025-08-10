from datetime import datetime


def parse_local_datetime(dt_str):
    try:
        # 1. ISO 8601 with tz (e.g. 2025-07-08T20:33:15-05:00)
        return datetime.fromisoformat(dt_str)
    except ValueError:
        pass
    try:
        # 2. With microseconds
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        pass
    try:
        # 3. Without microseconds
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:
        # 4. With slashes and literal T (e.g. 4/21/2025 T16:21:00)
        return datetime.strptime(dt_str, "%m/%d/%Y T%H:%M:%S")
    except ValueError as e:
        raise ValueError(f"Unrecognized date format: {dt_str}") from e