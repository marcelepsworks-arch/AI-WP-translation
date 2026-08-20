import threading

from app.storage.translation_memory import TranslationMemory


def _memory(tmp_path):
    return TranslationMemory(tmp_path / "tm.sqlite3")


def test_a_remembered_translation_comes_back(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("Request a quote", "es", "fp1") == "Solicitar presupuesto"


def test_an_unknown_source_misses(tmp_path):
    assert _memory(tmp_path).lookup("never seen", "es", "fp1") is None


def test_a_different_target_language_misses(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("Request a quote", "fr", "fp1") is None


def test_a_changed_fingerprint_misses(tmp_path):
    # Editing a prompt or the glossary must not keep serving translations
    # produced by the previous configuration.
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("Request a quote", "es", "fp2") is None


def test_context_is_not_part_of_the_key(tmp_path):
    # The same boilerplate under different headings is one entry -- that is
    # the entire point, and where the savings come from.
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("Request a quote", "es", "fp1") == "Solicitar presupuesto"


def test_whitespace_and_case_differences_are_distinct_entries(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("request a quote", "es", "fp1") is None
    assert tm.lookup("Request a quote ", "es", "fp1") is None


def test_remembering_the_same_key_twice_updates_it(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Pedir presupuesto", "es", "fp1")
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")

    assert tm.lookup("Request a quote", "es", "fp1") == "Solicitar presupuesto"
    assert tm.stats()["entries"] == 1


def test_hits_are_counted(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")
    tm.lookup("Request a quote", "es", "fp1")
    tm.lookup("Request a quote", "es", "fp1")

    assert tm.stats() == {"entries": 1, "hits": 2}


def test_a_miss_does_not_count_as_a_hit(tmp_path):
    tm = _memory(tmp_path)
    tm.remember("Request a quote", "Solicitar presupuesto", "es", "fp1")
    tm.lookup("something else", "es", "fp1")

    assert tm.stats()["hits"] == 0


def test_entries_survive_a_restart(tmp_path):
    TranslationMemory(tmp_path / "tm.sqlite3").remember("Free", "Gratuito", "es", "fp1")

    assert TranslationMemory(tmp_path / "tm.sqlite3").lookup("Free", "es", "fp1") == "Gratuito"


def test_inline_html_is_stored_verbatim(tmp_path):
    tm = _memory(tmp_path)
    source = 'Use 2x <a href="https://example.com/k">Starter Kits</a>.'
    translated = 'Usa 2x <a href="https://example.com/k">Kits Iniciales</a>.'
    tm.remember(source, translated, "es", "fp1")

    assert tm.lookup(source, "es", "fp1") == translated


def test_concurrent_access_from_many_threads_is_safe(tmp_path):
    # Blocks translate on a ThreadPoolExecutor, so lookups and writes race.
    tm = _memory(tmp_path)
    errors: list[Exception] = []

    def work(i: int) -> None:
        try:
            tm.remember(f"term {i}", f"término {i}", "es", "fp1")
            tm.lookup(f"term {i}", "es", "fp1")
        except Exception as exc:  # noqa: BLE001 -- recorded and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert tm.stats() == {"entries": 25, "hits": 25}
