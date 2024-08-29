import os

from ryz.core import Err, Ok, Res


def get(key: str, default: str | None = None) -> Res[str]:
    s = os.environ.get(key, default)
    if s is None:
        return Err(f"cannot find environ {key}")
    return Ok(s)

def get_bool(key: str, default: str | None = None) -> Res[bool]:
    env_val = get(key, default)

    match env_val:
        case "0":
            return Ok(False)
        case "1":
            return Ok(True)
        case _:
            return Err(
                f"key expected to be \"1\" or \"0\", but got {key} which",
            )
