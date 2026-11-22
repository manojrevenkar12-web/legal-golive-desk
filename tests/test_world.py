import ast
import copy
import json
from pathlib import Path

from golive.eval.run import load
from golive.world.world import FOUND_BY, World, simulate

PRODUCT_MODULES = ["golive/sso.py", "golive/dms.py", "golive/residency.py", "golive/questionnaire.py", "golive/delivery.py", "golive/service/app.py"]


def imports(path):
    tree = ast.parse(Path(path).read_text())
    return {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}


def test_the_product_never_imports_the_world():
    for m in PRODUCT_MODULES:
        assert not {i for i in imports(m) if i.startswith(("golive.world", "golive.eval"))}, m


def test_the_world_reads_only_its_own_config(monkeypatch):
    read = []
    real = Path.read_text

    def spy(self, *a, **k):
        read.append(self.name)
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    World(1)
    assert set(read) <= {"world.json"}
    assert "product.json" not in "".join(Path(p).read_text() for p in ["golive/world/world.py", "golive/world/artifacts.py"])


def test_same_seed_same_world_and_simulation_does_not_change_it():
    a, b = World(2), World(2)
    assert [(c.id, c.arrival, sorted(c.planted)) for c in a.customers] == [(c.id, c.arrival, sorted(c.planted)) for c in b.customers]
    before = copy.deepcopy([(c.id, c.arrival, sorted(c.planted), c.firewall_weeks) for c in a.customers])
    designs, product = load("designs"), load("product")
    out = {n: simulate(a, d, product)[0] for n, d in designs.items()}
    assert [(c.id, c.arrival, sorted(c.planted), c.firewall_weeks) for c in a.customers] == before
    # same luck: every design meets the same customers, arriving in the same weeks
    arrivals = {n: [(o.customer, o.arrival) for o in os] for n, os in out.items()}
    assert len({json.dumps(v) for v in arrivals.values()}) == 1


def test_simulation_is_deterministic():
    d, p = load("designs")["desk"], load("product")
    x = [o.golive for o in simulate(World(3), d, p)[0]]
    y = [o.golive for o in simulate(World(3), d, p)[0]]
    assert x == y


def test_checkers_find_planted_problems_from_the_files_alone():
    w = World(1)
    planted = sum(len(c.planted) for c in w.customers)
    assert planted > 50
    assert sum(len(c.detected) for c in w.customers) == planted
    assert sum(c.false_alarms for c in w.customers) == 0
    assert set().union(*(c.planted for c in w.customers)) <= set(FOUND_BY)
