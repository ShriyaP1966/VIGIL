"""Split a pasted transcript of "Speaker: text" lines into speaker turns."""

import re

_TURN = re.compile(r"^\s*([A-Za-z][A-Za-z ]{0,19}?)\s*:\s*(.*?)\s*$")


def parse_labelled_turns(text: str) -> list[dict] | None:
    """Return [{"speaker", "text"}, ...] when `text` looks like a labelled transcript, else None.

    A transcript needs at least two labelled lines from at least two different speakers, and no
    unlabelled text before the first label. Unlabelled lines continue the previous turn.
    """
    turns: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _TURN.match(line)
        if m:
            turns.append({"speaker": m.group(1).strip().lower(), "text": m.group(2)})
        elif turns:
            turns[-1]["text"] = (turns[-1]["text"] + "\n" + line.strip()).strip()
        else:
            return None
    if len(turns) < 2 or len({t["speaker"] for t in turns}) < 2:
        return None
    return turns
