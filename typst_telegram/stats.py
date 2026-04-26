from csv import DictReader, DictWriter
from datetime import datetime, timezone
from pathlib import Path


def _find_active(base: Path) -> Path:
    if not base.exists():
        return base
    i = 1
    while True:
        p = Path(f'{base}.{i}')
        if not p.exists():
            return p
        i += 1


class UserStats:

    COLUMNS = ('user_id', 'username', 'first_name', 'first_seen')

    def __init__(self, base: Path):
        self._active = _find_active(base)

    def record(self, user_id: int, username: str | None, first_name: str):
        write_header = not self._active.exists()
        row = {
            'user_id': user_id,
            'username': username or '',
            'first_name': first_name,
            'first_seen': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }
        with open(self._active, 'a', newline='', encoding='utf-8') as fin:
            w = DictWriter(fin, fieldnames=UserStats.COLUMNS)
            if write_header:
                w.writeheader()
            w.writerow(row)
