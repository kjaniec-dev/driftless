from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Position:
    isin: str
    value_pln: float
    label: str | None = None


@dataclass(frozen=True)
class Target:
    isin: str
    weight: float


@dataclass(frozen=True)
class Portfolio:
    base_currency: str
    cash_pln: float
    positions: tuple[Position, ...]
    targets: tuple[Target, ...]
    as_of: str | None = None


@dataclass(frozen=True)
class BuyOrder:
    isin: str
    label: str | None
    current_pln: float
    target_pln: float
    current_weight: float
    target_weight: float
    drift_pp: float
    buy_pln: float


@dataclass(frozen=True)
class RebalancePlan:
    total_pln: float
    positions_pln: float
    cash_pln: float
    orders: tuple[BuyOrder, ...]
    cash_deployed: float
    leftover_cash: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
