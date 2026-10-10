from algo.train.detect import select_device


def test_auto_device_falls_back_to_cpu_when_cuda_unavailable(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    )
    assert select_device("auto") == "cpu"
    assert select_device("cpu") == "cpu"


def test_auto_device_uses_cuda_when_available(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
    )
    assert select_device("auto") == 0
