"""Reproduce report experiments without changing the submitted client/config.

Run: python scripts/run_experiments.py
Outputs: reports/experiments.json (seed 25).
"""
from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gameday_lab.client import ResilientClient
from gameday_lab.factory import build_client
from gameday_lab.sim.config import load_config
from gameday_lab.sim.engine import evaluate_checks, run_scenario


class UnfilteredClient(ResilientClient):
    """Deliberately unsafe control, used ONLY for the tool-capability experiment."""

    def ladder(self, task: str) -> list[str]:
        return list(self.order)


def main() -> None:
    cfg = load_config()
    cache_cfg = load_config("configs/gameday.yaml", "configs/scenarios_cache.yaml")
    seed = 25
    results: dict = {"seed": seed, "client_settings": cfg.client, "cache_settings": cfg.cache,
                     "budget": {}, "timeout": {}, "capability": {}, "cache": {}}

    def measure(config, scenario, client):
        metrics = run_scenario(config, scenario, client, seed=seed).metrics()
        checks = evaluate_checks(metrics, config.scenarios[scenario].checks)
        return {**metrics, "checks": checks, "pass": all(checks.values())}

    # Two independent defenses: disable breaker, enable/disable retry budget.
    for breaker_enabled in (False, True):
        for budget_enabled in (True, False):
            settings = copy.deepcopy(cfg.client)
            settings["max_attempts_per_provider"] = 5
            if not breaker_enabled:
                settings["breaker"]["min_calls"] = 1000000000
            if not budget_enabled:
                settings.update(retry_budget_ratio=100, retry_budget_max_tokens=1e9,
                                retry_budget_min_per_s=1e6)
            label = f"breaker_{'on' if breaker_enabled else 'off'}_budget_{'on' if budget_enabled else 'off'}"
            variant = replace(cfg, client=settings)
            results["budget"][label] = {
                key: measure(variant, key, build_client("resilient", variant))
                for key in ("G2_overload_storm", "G3_brownout")
            }

    for timeout in (cfg.client["attempt_timeout_s"], 30):
        settings = {**cfg.client, "attempt_timeout_s": timeout}
        variant = replace(cfg, client=settings)
        results["timeout"][str(timeout)] = {
            key: measure(variant, key, build_client("resilient", variant))
            for key in ("G6_provider_outage", "G4_slow_region")
        }

    for filtered in (True, False):
        client = (build_client("resilient", cfg) if filtered else
                  UnfilteredClient(cfg.provider_infos(), cfg.fallback_order, cfg.client, seed=1))
        results["capability"]["filtered" if filtered else "unfiltered"] = measure(
            cfg, "G6_provider_outage", client)

    variants = {
        "starter": {"similarity_threshold": 0.80, "ttl_s": 600, "max_stale_s": 0},
        "final": {},
        "threshold_0.80": {"similarity_threshold": 0.80},
        "threshold_0.97": {"similarity_threshold": 0.97},
        "ttl_30": {"ttl_s": 30},
        "ttl_300": {"ttl_s": 300},
        "no_stale": {"max_stale_s": 0},
    }
    for label, changes in variants.items():
        variant = replace(cache_cfg, cache={**cache_cfg.cache, **changes})
        results["cache"][label] = measure(variant, "C1_faq_outage", build_client("cached", variant))

    out = Path("reports/experiments.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved report experiments to {out}")
    for group in ("budget", "timeout", "capability", "cache"):
        print(group + ": " + ", ".join(results[group]))


if __name__ == "__main__":
    main()
