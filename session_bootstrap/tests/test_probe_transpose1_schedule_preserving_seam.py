from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "session_bootstrap"
    / "scripts"
    / "probe_transpose1_schedule_preserving_seam.py"
)
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
probe_spec = importlib.util.spec_from_file_location(
    "probe_transpose1_schedule_preserving_seam",
    SCRIPT_PATH,
)
if probe_spec is None or probe_spec.loader is None:
    raise RuntimeError(f"unable to load module from {SCRIPT_PATH}")
module = importlib.util.module_from_spec(probe_spec)
probe_spec.loader.exec_module(module)


class DummyTVMScriptNamespace:
    def __getattr__(self, name: str):
        if name in {"ir_module", "prim_func"}:
            return lambda obj: obj
        return self

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return self


class FakeGlobalVar:
    def __init__(self, name_hint: str) -> None:
        self.name_hint = name_hint


class FakeFunc:
    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.attrs: dict[str, object] = {}

    def with_attr(self, key: str, value: object):
        cloned = FakeFunc(self.tag)
        cloned.attrs = dict(self.attrs)
        cloned.attrs[key] = value
        return cloned


class FakeIRModule:
    def __init__(self, mapping: dict[str, object]) -> None:
        self.mapping = dict(mapping)

    def get_global_var(self, name: str) -> FakeGlobalVar:
        if name not in self.mapping:
            raise KeyError(name)
        return FakeGlobalVar(name)

    def __getitem__(self, key: object) -> object:
        name = getattr(key, "name_hint", key)
        if not isinstance(name, str) or name not in self.mapping:
            raise KeyError(name)
        return self.mapping[name]

    def __setitem__(self, key: object, value: object) -> None:
        name = getattr(key, "name_hint", key)
        if not isinstance(name, str):
            raise KeyError(name)
        self.mapping[name] = value


class ProbeTranspose1SchedulePreservingSeamTest(unittest.TestCase):
    def test_lookup_global_func_finds_named_entry(self) -> None:
        mod = FakeIRModule({"main": {"tag": "scheduled"}})
        self.assertEqual(module.lookup_global_func(mod, "main"), {"tag": "scheduled"})

    def test_replace_global_func_updates_named_entry(self) -> None:
        mod = FakeIRModule({"fused_conv2d_transpose1_add9": FakeFunc("scheduled")})
        updated = module.replace_global_func(
            mod,
            "fused_conv2d_transpose1_add9",
            FakeFunc("candidate"),
        )
        self.assertIs(updated, mod)
        replaced = mod.mapping["fused_conv2d_transpose1_add9"]
        self.assertIsInstance(replaced, FakeFunc)
        self.assertEqual(replaced.tag, "candidate")
        self.assertEqual(replaced.attrs.get("global_symbol"), "fused_conv2d_transpose1_add9")

    def test_load_candidate_override_recovers_checked_in_candidate_source(self) -> None:
        script_module = types.ModuleType("tvm.script")
        script_module.ir = DummyTVMScriptNamespace()
        script_module.tir = DummyTVMScriptNamespace()
        tvm_module = types.ModuleType("tvm")
        tvm_module.script = script_module

        with mock.patch.dict(
            sys.modules,
            {
                "tvm": tvm_module,
                "tvm.script": script_module,
            },
            clear=False,
        ):
            payload = module.load_candidate_override(
                module.DEFAULT_CANDIDATE_IMPL,
                {
                    "legalized_fused_tir": {
                        "tasks": [
                            {
                                "rank": 16,
                                "task_name": "fused_conv2d_transpose1_add9",
                                "prim_funcs": ["fused_conv2d_transpose1_add9"],
                            }
                        ]
                    }
                },
            )

        self.assertEqual(payload["metadata"]["operator"], "fused_conv2d_transpose1_add9")
        self.assertEqual(payload["override"]["kind"], "replace_prim_func_from_source")
        self.assertEqual(payload["source_func_name"], "main")
        self.assertTrue(callable(payload["source_func"]))
        self.assertEqual(
            payload["result"]["evaluation_contract"]["path_kind"],
            "diagnostic_raw_pre_compile_replacement",
        )


if __name__ == "__main__":
    unittest.main()
