from __future__ import annotations

import inspect

from .base import MarketState, QuoteTarget, Strategy
from .quoting import AvellanedaStoikov, AvellanedaStoikovSignal, FixedSpread

STRATEGIES: dict[str, type[Strategy]] = {
    cls.name: cls for cls in (FixedSpread, AvellanedaStoikov, AvellanedaStoikovSignal)
}


def accepted_params(cls: type[Strategy]) -> set[str]:
    names: set[str] = set()
    for c in cls.__mro__:
        if "__init__" in vars(c):
            names |= {p for p in inspect.signature(c.__init__).parameters if p not in ("self", "kw")}
    return names


def make_strategy(name: str, strict: bool = True, **params) -> Strategy:
    """Build a strategy by name. With strict=False, parameters the strategy does
    not take are ignored (handy when one parameter set is shared by a sweep)."""
    try:
        cls = STRATEGIES[name]
    except KeyError:
        raise ValueError(f"unknown strategy {name!r}; choose from {sorted(STRATEGIES)}") from None
    ok = accepted_params(cls)
    unknown = set(params) - ok
    if unknown and strict:
        raise ValueError(f"{name} does not take {sorted(unknown)}; it takes {sorted(ok)}")
    return cls(**{k: float(v) for k, v in params.items() if k in ok})


__all__ = ["STRATEGIES", "accepted_params", "make_strategy", "MarketState", "QuoteTarget", "Strategy",
           "FixedSpread", "AvellanedaStoikov", "AvellanedaStoikovSignal"]
