from idse_orchestrator.compiler.merger import merge_profiles


def test_merge_profiles():
    blueprint = {
        "id": "agent",
        "name": "Base",
        "goals": ["a"],
        "runtime_hints": {"x": 1, "nested": {"y": 1}},
    }
    feature = {
        "name": "Feature",
        "goals": ["b"],
        "runtime_hints": {"nested": {"y": 2}, "z": 3},
    }

    merged = merge_profiles(blueprint, feature)
    assert merged["name"] == "Feature"
    assert merged["goals"] == ["b"]
    assert merged["runtime_hints"]["nested"]["y"] == 2
    assert merged["runtime_hints"]["x"] == 1
    assert merged["runtime_hints"]["z"] == 3
