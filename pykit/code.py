from inspect import isfunction
from pykit.err import ValErr
from pykit.lock import Lock
from typing import Generic, Iterable, TypeVar
from pydantic import BaseModel

from pykit.obj import get_fqname
from pykit.res import Err, Ok, Res
from pykit.log import log


T = TypeVar("T")
class Coded(BaseModel, Generic[T]):
    """
    Arbitrary data coupled with identification code.

    Useful when data is type that doesn't support ``code() -> str`` signature.
    """
    code: str
    val: T

class Code:
    """
    Manages attached to various objects str codes.
    """
    _code_to_type: dict[str, type] = {}
    _codes: list[str] = []
    _lock: Lock = Lock()

    @classmethod
    def has_code(cls, code: str) -> bool:
        return code in cls._codes

    @classmethod
    async def get_registered_code_by_id(cls, id: int) -> Res[str]:
        await cls._lock.wait()
        if id > len(cls._codes) - 1:
            return Err(ValErr(f"codeid {id} is not registered"))
        return Ok(cls._codes[id])

    @classmethod
    async def get_registered_codes(cls) -> Res[list[str]]:
        await cls._lock.wait()
        return Ok(cls._codes.copy())

    @classmethod
    async def get_registered_code_by_type(cls, t: type) -> Res[str]:
        await cls._lock.wait()
        for c, t_ in cls._code_to_type.items():
            if t_ is t:
                return Ok(c)
        return Err(ValErr(f"type {t} is not registered"))

    @classmethod
    async def get_registered_codeid(cls, code: str) -> Res[int]:
        await cls._lock.wait()
        if code not in cls._codes:
            return Err(ValErr(f"code {code} is not registered"))
        return Ok(cls._codes.index(code))

    @classmethod
    async def get_registered_type(cls, code: str) -> Res[type]:
        await cls._lock.wait()
        if code not in cls._code_to_type:
            return Err(ValErr(f"code {code} is not registered"))
        return Ok(cls._code_to_type[code])

    @classmethod
    async def upd(
            cls,
            types: Iterable[type],
            order: list[str] | None = None) -> Res[None]:
        async with cls._lock:
            for t in types:
                code_res = cls.get_from_type(t)
                if isinstance(code_res, Err):
                    log.err(
                        f"cannot get code {code}: {code_res.errval}"
                        " => skip")
                    continue
                code = code_res.okval

                validate_res = cls.validate(code)
                if isinstance(validate_res, Err):
                    log.err(
                        f"code {code} is not valid:"
                        f" {validate_res.errval} => skip")
                    continue

                cls._code_to_type[code] = t

            cls._codes = list(cls._code_to_type.keys())
            if order:
                order_res = cls._order(order)
                if isinstance(order_res, Err):
                    return order_res

            return Ok(None)

    @classmethod
    def _order(cls, order: list[str]) -> Res[None]:
        sorted_codes: list[str] = []
        for o in order:
            if o not in cls._codes:
                log.warn(f"unrecornized order code {o} => skip")
                continue
            cls._codes.remove(o)
            sorted_codes.append(o)
        # bring rest of the codes
        for c in cls._codes:
            sorted_codes.append(c)

        cls._codes = sorted_codes
        return Ok(None)

    @classmethod
    def validate(cls, code: str) -> Res[None]:
        if not isinstance(code, str):
            return Err(ValErr(f"code {code} must be str"))
        if code == "":
            return Err(ValErr(f"empty code"))
        for i, c in enumerate(code):
            if i == 0 and not c.isalpha():
                return Err(ValErr(
                    f"code {code} must start with alpha"))
            if not c.isalnum() and c != "_":
                return Err(ValErr(
                    f"code {code} can contain only alnum"
                    " characters or underscore"))
        if len(code) > 256:
            return Err(ValErr(f"code {code} exceeds maxlen 256"))
        return Ok(None)

    @classmethod
    def get_from_type(cls, t: type) -> Res[str]:
        if isinstance(t, Coded):
            code = t.code
        else:
            codefn = getattr(t, "code", None)
            if codefn is None:
                return Err(ValErr(
                    f"msg data {t} must define \"code() -> str\" method"))
            if not isfunction(codefn):
                return Err(ValErr(
                    f"msg data {t} \"code\" attribute must be function,"
                    f" got {codefn}"))
            try:
                code = codefn()
            except Exception as err:
                log.catch(err)
                return Err(ValErr(
                    f"err {get_fqname(err)} occured during"
                    f" msg data {t} {codefn} method call #~stacktrace"))

        validate_res = cls.validate(code)
        if isinstance(validate_res, Err):
            return validate_res

        return Ok(code)
