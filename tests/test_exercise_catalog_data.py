import ast
import unittest
from pathlib import Path

from app.core.exercise_catalog import EXERCISE_CATALOG


def _load_allowed_custom_exercise_slugs() -> set[str]:
    program_schema_path = (
        Path(__file__).resolve().parents[1] / "app" / "schemas" / "program.py"
    )
    tree = ast.parse(program_schema_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALLOWED_CUSTOM_EXERCISE_SLUGS":
                    return set(ast.literal_eval(node.value))
    raise AssertionError("ALLOWED_CUSTOM_EXERCISE_SLUGS not found in app/schemas/program.py")


def _personalized_plan_tree() -> ast.Module:
    personalized_plan_path = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "personalized_plan.py"
    )
    return ast.parse(personalized_plan_path.read_text(encoding="utf-8"))


def _load_exercise_library_slugs() -> list[str]:
    tree = _personalized_plan_tree()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXERCISE_LIBRARY":
                    raw = ast.literal_eval(node.value)
                    return list(raw.keys())
    raise AssertionError("EXERCISE_LIBRARY not found in app/services/personalized_plan.py")


def _load_exercise_pool_rules() -> tuple[list[str], set[str], list[str]]:
    tree = _personalized_plan_tree()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_exercise_pool":
            recovery_base: list[str] | None = None
            beginner_allowed: set[str] | None = None
            fallback_pool: list[str] | None = None
            for child in ast.walk(node):
                if isinstance(child, ast.If) and isinstance(child.test, ast.Name) and child.test.id == "recovery":
                    for stmt in child.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and target.id == "base":
                                    recovery_base = list(ast.literal_eval(stmt.value))
                if (
                    isinstance(child, ast.If)
                    and isinstance(child.test, ast.Compare)
                    and isinstance(child.test.left, ast.Name)
                    and child.test.left.id == "level"
                    and len(child.test.ops) == 1
                    and isinstance(child.test.ops[0], ast.Eq)
                    and len(child.test.comparators) == 1
                    and isinstance(child.test.comparators[0], ast.Constant)
                    and child.test.comparators[0].value == "beginner"
                ):
                    for stmt in child.body:
                        if (
                            isinstance(stmt, ast.Assign)
                            and isinstance(stmt.value, ast.ListComp)
                            and isinstance(stmt.value.generators[0].iter, ast.Name)
                            and stmt.value.generators[0].iter.id == "pool"
                        ):
                            comparison = stmt.value.generators[0].ifs[0]
                            if (
                                isinstance(comparison, ast.Compare)
                                and len(comparison.ops) == 1
                                and isinstance(comparison.ops[0], ast.In)
                            ):
                                beginner_allowed = set(ast.literal_eval(comparison.comparators[0]))
                if (
                    isinstance(child, ast.If)
                    and isinstance(child.test, ast.UnaryOp)
                    and isinstance(child.test.op, ast.Not)
                    and isinstance(child.test.operand, ast.Name)
                    and child.test.operand.id == "pool"
                ):
                    for stmt in child.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and target.id == "pool":
                                    fallback_pool = list(ast.literal_eval(stmt.value))
            if recovery_base is None or beginner_allowed is None or fallback_pool is None:
                raise AssertionError("Failed to parse _exercise_pool rules from personalized_plan.py")
            return recovery_base, beginner_allowed, fallback_pool
    raise AssertionError("_exercise_pool not found in app/services/personalized_plan.py")


class ExerciseCatalogDataTests(unittest.TestCase):
    def test_catalog_order_is_exact_six_reference_exercises(self) -> None:
        self.assertEqual(
            [item["slug"] for item in EXERCISE_CATALOG],
            ["squat", "pushup", "lunge", "glute_bridge", "leg_raise", "crunch"],
        )

    def test_custom_program_allows_only_new_canonical_slugs(self) -> None:
        self.assertEqual(
            _load_allowed_custom_exercise_slugs(),
            {"squat", "pushup", "lunge", "glute_bridge", "leg_raise", "crunch"},
        )

    def test_personalized_plan_uses_same_six_exercises(self) -> None:
        self.assertEqual(
            _load_exercise_library_slugs(),
            ["squat", "pushup", "lunge", "glute_bridge", "leg_raise", "crunch"],
        )

    def test_personalized_plan_workout_and_recovery_pools_match_new_catalog(self) -> None:
        recovery_base, beginner_allowed, fallback_pool = _load_exercise_pool_rules()
        self.assertEqual(
            beginner_allowed,
            {"squat", "pushup", "lunge", "glute_bridge", "leg_raise", "crunch"},
        )
        self.assertEqual(
            recovery_base,
            ["glute_bridge", "leg_raise", "crunch", "squat"],
        )
        self.assertEqual(
            fallback_pool,
            ["glute_bridge", "leg_raise", "crunch", "squat"],
        )


if __name__ == "__main__":
    unittest.main()
