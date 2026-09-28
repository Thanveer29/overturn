from app.services.citations import extract_case_ids


def test_extract_case_ids_finds_all_unique_references():
    text = (
        "The appeal cited case HC-018 as a warning, and also referenced HC-003 "
        "and HC-007. Later it mentioned HC-018 again."
    )
    assert extract_case_ids(text) == {"HC-018", "HC-003", "HC-007"}


def test_extract_case_ids_empty_when_no_citations():
    assert extract_case_ids("Generic advice with no historical references.") == set()
