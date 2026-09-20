from warsignal.mission.queue import mark_failed, pop_next


def test_queue_pop_and_failed(tmp_path, monkeypatch):
    queue = tmp_path / "queue.txt"
    queue.write_text("\nfirst\nsecond\n")
    progress = tmp_path / "in_progress.txt"
    monkeypatch.setattr("warsignal.mission.queue.ROOT", tmp_path)
    assert pop_next(queue) == "first"
    assert queue.read_text() == "\nsecond\n"
    mark_failed("first", "bad")
    assert "first\tbad" in (tmp_path / "failed.txt").read_text()


def test_empty_queue(tmp_path):
    assert pop_next(tmp_path / "none.txt") is None
