from rag.retrieval import HybridRetriever


def test_extract_version():
    f = HybridRetriever._extract_version
    assert f("Does v2.1 support X?") == "v2.1"
    assert f("I'm on V2.0, steps?").lower() == "v2.0"
    assert f("no version here") is None

