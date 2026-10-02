"""The one LLM client: provider switch from env, strict JSON output, every call cached on disk, cost counted.

Village text goes to the model, so every request asks the router to skip providers that keep or train on prompts
(dataset terms: no training on the data).
"""

import copy
import hashlib
import json
import os
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass

from openai import OpenAI
from pydantic import BaseModel

from heirloom.config import ROOT

CACHE = ROOT / "cache" / "llm"

PROVIDERS = {
    # name: (base_url, env var holding the key)
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}
# Cheapest endpoint that still refuses to keep or train on prompts and supports strict JSON output.
ROUTING = {"data_collection": "deny", "require_parameters": True, "sort": "price"}


class SpendLimitReached(RuntimeError):
    pass


def spent_so_far() -> float:
    """Every dollar this project has paid, summed from the saved calls."""
    total = 0.0
    for path in CACHE.glob("*/*.json"):
        try:
            total += json.loads(path.read_text(encoding="utf-8"))["usage"].get("cost") or 0.0
        except (OSError, ValueError, KeyError):
            continue
    return total


@dataclass
class Usage:
    calls: int = 0
    cached: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON schema with $refs inlined and titles dropped: the form every provider's strict mode accepts."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


class LLM:
    def __init__(self) -> None:
        provider = os.environ.get("LLM_PROVIDER", "openrouter")
        if provider not in PROVIDERS:
            raise ValueError(f"LLM_PROVIDER={provider!r} is not one of {', '.join(PROVIDERS)}")
        base_url, key_env = PROVIDERS[provider]
        self.provider = provider
        self.client = OpenAI(base_url=base_url, api_key=os.environ[key_env], max_retries=6, timeout=300)
        self.cheap = os.environ["LLM_MODEL_CHEAP"]
        self.strong = os.environ["LLM_MODEL_STRONG"]
        self.usage: dict[str, Usage] = defaultdict(Usage)
        self._lock = threading.Lock()
        # Hard cap on the project's total spend. Not set = no new paid calls at all.
        self.spent = spent_so_far()
        self.limit = float(os.environ.get("LLM_SPEND_LIMIT_USD") or self.spent)

    def structured[T: BaseModel](self, model: str, system: str, user: str, schema: type[T],
                                 effort: str = "low") -> T:
        """One call whose answer must match `schema`. Same request twice = read from disk, free."""
        from heirloom.privacy import scrub_secrets  # credentials never leave the machine

        user = scrub_secrets(user)
        request = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": schema.__name__, "strict": True, "schema": strict_schema(schema)}},
            "reasoning": {"effort": effort},
        }
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        path = CACHE / key[:2] / f"{key}.json"
        if path.exists():
            with self._lock:
                self.usage[model].cached += 1
            return schema.model_validate(json.loads(path.read_text(encoding="utf-8"))["output"])

        with self._lock:
            if self.spent >= self.limit:
                raise SpendLimitReached(
                    f"LLM spend ${self.spent:.2f} has reached LLM_SPEND_LIMIT_USD=${self.limit:.2f}. "
                    "No call was made. Raise the limit in .env to continue.")
        resp = self.client.chat.completions.create(
            model=model,
            messages=request["messages"],
            response_format=request["response_format"],
            extra_body={"provider": ROUTING, "reasoning": request["reasoning"]},
        )
        output = schema.model_validate_json(resp.choices[0].message.content)
        usage = resp.usage.model_dump() if resp.usage else {}
        with self._lock:
            u = self.usage[model]
            u.calls += 1
            u.prompt_tokens += usage.get("prompt_tokens") or 0
            u.completion_tokens += usage.get("completion_tokens") or 0
            u.cost += usage.get("cost") or 0.0
            self.spent += usage.get("cost") or 0.0

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "request": request,
            "output": output.model_dump(mode="json"),
            "usage": usage,
            "served_by": {"model": resp.model, "provider": getattr(resp, "provider", None)},
        }, ensure_ascii=False), encoding="utf-8")
        return output

    def report(self) -> dict:
        return {"provider": self.provider, "routing": ROUTING,
                "by_model": {m: asdict(u) for m, u in self.usage.items()},
                "total_cost": round(sum(u.cost for u in self.usage.values()), 6),
                "project_spent": round(self.spent, 4), "project_limit": self.limit}
