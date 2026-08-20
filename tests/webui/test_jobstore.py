import threading

from app.webui.jobstore import JobStore


def test_a_created_job_can_be_read_back(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create("abc", {"status": "running", "post_id": 12, "action": "translate"})

    assert store.get("abc")["status"] == "running"
    assert store.get("abc")["post_id"] == 12


def test_update_merges_fields_instead_of_replacing_them(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create("abc", {"status": "running", "post_id": 12})
    store.update("abc", status="done", translated_post_id=981)

    job = store.get("abc")
    assert job == {"status": "done", "post_id": 12, "translated_post_id": 981}


def test_unknown_job_reads_as_none(tmp_path):
    assert JobStore(tmp_path / "jobs.sqlite3").get("nope") is None


def test_updating_an_unknown_job_is_a_no_op(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.update("nope", status="done")

    assert store.get("nope") is None


def test_jobs_survive_a_restart(tmp_path):
    # The whole point of the store: today's in-memory dict loses every job
    # when the dashboard restarts, so "what did I run yesterday" is gone.
    path = tmp_path / "jobs.sqlite3"
    JobStore(path).create("abc", {"status": "done", "post_id": 12})

    assert JobStore(path).get("abc")["status"] == "done"


def test_recent_jobs_come_back_newest_first(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    for job_id in ("one", "two", "three"):
        store.create(job_id, {"status": "done"})

    assert [j["job_id"] for j in store.list_recent()] == ["three", "two", "one"]


def test_recent_jobs_respect_the_limit(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    for job_id in ("one", "two", "three"):
        store.create(job_id, {"status": "done"})

    assert [j["job_id"] for j in store.list_recent(limit=2)] == ["three", "two"]


def test_listed_jobs_carry_their_id_and_timestamps(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create("abc", {"status": "running"})

    job = store.list_recent()[0]
    assert job["job_id"] == "abc"
    assert job["created_at"] and job["updated_at"]


def test_concurrent_updates_from_many_threads_do_not_lose_writes(tmp_path):
    # Jobs run on background threads and update their own row as they go.
    store = JobStore(tmp_path / "jobs.sqlite3")
    for i in range(20):
        store.create(f"job{i}", {"status": "running"})

    def finish(i: int) -> None:
        store.update(f"job{i}", status="done", index=i)

    threads = [threading.Thread(target=finish, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(store.get(f"job{i}") == {"status": "done", "index": i} for i in range(20))
