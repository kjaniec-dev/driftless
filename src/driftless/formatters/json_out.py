import json

from driftless.models import RebalancePlan


def plan_to_dict(plan: RebalancePlan) -> dict:
    return {
        "total_pln": round(plan.total_pln, 2),
        "positions_pln": round(plan.positions_pln, 2),
        "cash_pln": round(plan.cash_pln, 2),
        "cash_deployed": round(plan.cash_deployed, 2),
        "leftover_cash": round(plan.leftover_cash, 2),
        "warnings": list(plan.warnings),
        "orders": [
            {
                "isin": o.isin,
                "label": o.label,
                "current_weight": round(o.current_weight, 6),
                "target_weight": o.target_weight,
                "drift_pp": round(o.drift_pp, 2),
                "buy_pln": round(o.buy_pln, 2),
            }
            for o in plan.orders
        ],
    }


def format_json(plan: RebalancePlan) -> str:
    return json.dumps(plan_to_dict(plan), indent=2, ensure_ascii=False)
