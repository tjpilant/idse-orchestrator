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


def test_merge_profiles_blueprint_defaults_and_feature_overrides():
    blueprint = {
        "id": "base-agent",
        "name": "Base",
        "description": "default",
        "constraints": ["no-llm", "deterministic"],
        "memory_policy": {"retain_days": 7, "shared": False},
    }
    feature = {
        "name": "Feature",
        "constraints": ["deterministic"],
        "memory_policy": {"shared": True},
    }

    merged = merge_profiles(blueprint, feature)
    assert merged["id"] == "base-agent"
    assert merged["name"] == "Feature"
    assert merged["description"] == "default"
    assert merged["constraints"] == ["deterministic"]
    assert merged["memory_policy"]["retain_days"] == 7
    assert merged["memory_policy"]["shared"] is True
