"""Model A/B testing for comparing VLM performance"""
import logging
import random
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ModelVariant:
    """Configuration for a model variant in A/B test"""

    def __init__(
        self,
        name: str,
        model_name: str,
        weight: float = 1.0,
        config: Optional[dict[str, Any]] = None,
    ):
        self.name = name
        self.model_name = model_name
        self.weight = weight
        self.config = config or {}


class ABTestManager:
    """Manage A/B tests for model variants"""

    def __init__(self):
        self._tests: dict[str, dict] = {}
        self._metrics: dict[str, list] = {}

    def create_test(
        self,
        test_id: str,
        variants: list[ModelVariant],
        description: str = "",
    ) -> None:
        """Create a new A/B test"""
        total_weight = sum(v.weight for v in variants)
        normalized = []

        cumulative = 0.0
        for v in variants:
            cumulative += v.weight / total_weight
            normalized.append({
                "name": v.name,
                "model_name": v.model_name,
                "config": v.config,
                "cumulative_weight": cumulative,
            })

        self._tests[test_id] = {
            "id": test_id,
            "description": description,
            "variants": normalized,
            "created_at": datetime.utcnow(),
            "is_active": True,
        }
        self._metrics[test_id] = []

        logger.info(f"Created A/B test: {test_id} with {len(variants)} variants")

    def select_variant(
        self,
        test_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Select a variant for a request.

        Uses weighted random selection. Can be extended to use
        consistent hashing based on tenant_id for sticky sessions.
        """
        test = self._tests.get(test_id)
        if not test or not test["is_active"]:
            return None

        # Weighted random selection
        r = random.random()
        for variant in test["variants"]:
            if r <= variant["cumulative_weight"]:
                return variant

        return test["variants"][-1]

    def record_metric(
        self,
        test_id: str,
        variant_name: str,
        latency_ms: int,
        success: bool,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record performance metric for a variant"""
        if test_id not in self._metrics:
            self._metrics[test_id] = []

        self._metrics[test_id].append({
            "variant": variant_name,
            "latency_ms": latency_ms,
            "success": success,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
        })

    def get_test_results(self, test_id: str) -> Optional[dict]:
        """Get aggregated results for an A/B test"""
        test = self._tests.get(test_id)
        if not test:
            return None

        metrics = self._metrics.get(test_id, [])
        if not metrics:
            return {
                "test_id": test_id,
                "total_requests": 0,
                "variants": {},
            }

        # Aggregate by variant
        variant_stats: dict[str, dict] = {}
        for m in metrics:
            name = m["variant"]
            if name not in variant_stats:
                variant_stats[name] = {
                    "requests": 0,
                    "successes": 0,
                    "total_latency": 0,
                    "latencies": [],
                }

            stats = variant_stats[name]
            stats["requests"] += 1
            if m["success"]:
                stats["successes"] += 1
            stats["total_latency"] += m["latency_ms"]
            stats["latencies"].append(m["latency_ms"])

        # Calculate summary stats
        results = {}
        for name, stats in variant_stats.items():
            latencies = sorted(stats["latencies"])
            results[name] = {
                "requests": stats["requests"],
                "success_rate": stats["successes"] / stats["requests"] if stats["requests"] > 0 else 0,
                "avg_latency_ms": stats["total_latency"] / stats["requests"] if stats["requests"] > 0 else 0,
                "p50_latency_ms": latencies[len(latencies) // 2] if latencies else 0,
                "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
                "p99_latency_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0,
            }

        return {
            "test_id": test_id,
            "description": test["description"],
            "total_requests": len(metrics),
            "variants": results,
        }

    def list_tests(self) -> list[dict]:
        """List all A/B tests"""
        return [
            {
                "id": t["id"],
                "description": t["description"],
                "is_active": t["is_active"],
                "created_at": t["created_at"],
                "variant_count": len(t["variants"]),
            }
            for t in self._tests.values()
        ]

    def deactivate_test(self, test_id: str) -> bool:
        """Deactivate an A/B test"""
        if test_id in self._tests:
            self._tests[test_id]["is_active"] = False
            return True
        return False


# Global A/B test manager
_ab_manager: Optional[ABTestManager] = None


def get_ab_manager() -> ABTestManager:
    global _ab_manager
    if _ab_manager is None:
        _ab_manager = ABTestManager()
    return _ab_manager
