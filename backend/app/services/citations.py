import re

CASE_ID_PATTERN = re.compile(r"HC-\d{3}")


def extract_case_ids(text: str) -> set[str]:
    """Pull 'HC-###' historical-case references out of LLM/Hindsight output.

    Mirrors frontend/src/components/MemoryPanel.tsx's citation extraction --
    used here to score the evaluation harness, there to filter the UI's
    "why this recommendation" panel.
    """
    return set(CASE_ID_PATTERN.findall(text))
