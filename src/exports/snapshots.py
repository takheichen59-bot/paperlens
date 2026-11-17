"""Immutable export generations, one CURRENT commit, and leased reader snapshots."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
import os
import re
import shutil

from contracts import ResultStatus, validate_record

FILENAMES = ('results.jsonl', 'failures.jsonl', 'review.jsonl', 'warnings_by_severity.jsonl')


def record_digest(value):
    return sha256(_json(value).encode('utf-8')).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class ExportSnapshot:
    destination: Path
    version_id: str
    published_at: str
    directory: Path
    results_index: tuple[tuple[str, int, str, str], ...]
    files: tuple[tuple[str, str, int], ...]
    _lease: Path


@dataclass(frozen=True)
class WarningsBySeverityRecord:
    paper_id: str
    result_index: int
    result_sha256: str
    status: ResultStatus
    informational: tuple[str, ...]
    blocking: tuple[str, ...]


@contextmanager
def _lock(destination):
    """Serialize pointer selection/publication/pruning, including reader leases."""
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / '.publish.lock').open('a+b') as handle:
        try:
            import fcntl
        except ImportError:  # Standard-library Windows implementation.
            import msvcrt
            if handle.tell() == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _sync_directory(path):
    if os.name == 'nt':
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_jsonl(path, rows):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(_json(row) + '\n')
        handle.flush(); os.fsync(handle.fileno())


def _write_json(path, value):
    with path.open('x', encoding='utf-8') as handle:
        handle.write(_json(value) + '\n')
        handle.flush(); os.fsync(handle.fileno())


def publish_generation(destination, payloads, results_index):
    destination = Path(destination)
    if set(payloads) != set(FILENAMES):
        raise ValueError('Incomplete export generation')
    published_at = datetime.now(timezone.utc).isoformat()
    version_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-') + uuid4().hex
    with _lock(destination):
        versions = destination / 'versions'; versions.mkdir(exist_ok=True)
        stage = versions / ('.staging-' + version_id)
        final = versions / version_id
        pointer = destination / ('.CURRENT-' + uuid4().hex + '.tmp')
        stage.mkdir()
        committed = False
        try:
            files = []
            for name in FILENAMES:
                _write_jsonl(stage / name, payloads[name])
                files.append([name, sha256((stage / name).read_bytes()).hexdigest(), len(payloads[name])])
            _write_json(stage / 'manifest.json', {'version_id': version_id, 'published_at': published_at,
                'files': files, 'results_index': results_index})
            _sync_directory(stage)
            os.replace(stage, final)
            _sync_directory(versions)
            _write_json(pointer, {'version_id': version_id, 'published_at': published_at})
            os.replace(pointer, destination / 'CURRENT')
            committed = True
            _sync_directory(destination)
        finally:
            pointer.unlink(missing_ok=True)
            shutil.rmtree(stage, ignore_errors=True)
            if not committed:
                shutil.rmtree(final, ignore_errors=True)
    return final


@contextmanager
def open_current_snapshot(destination):
    destination = Path(destination)
    with _lock(destination):
        pointer = json.loads((destination / 'CURRENT').read_text(encoding='utf-8'))
        version = pointer['version_id']
        if not isinstance(version, str) or not re.fullmatch(r'\d{8}T\d{12}Z-[0-9a-f]{32}', version):
            raise ValueError('Invalid export version')
        directory = destination / 'versions' / version
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        if manifest['version_id'] != version or manifest['published_at'] != pointer['published_at']:
            raise ValueError('Export pointer identity mismatch')
        if set(f[0] for f in manifest['files']) != set(FILENAMES):
            raise ValueError('Incomplete export manifest')
        leases = destination / '.leases'; leases.mkdir(exist_ok=True)
        lease = leases / (uuid4().hex + '.json')
        _write_json(lease, {'version_id': version, 'pid': os.getpid()})
        snapshot = ExportSnapshot(destination, version, pointer['published_at'], directory,
            tuple(tuple(r) for r in manifest['results_index']), tuple(tuple(f) for f in manifest['files']), lease)
    try:
        yield snapshot
    finally:
        with _lock(destination):
            lease.unlink(missing_ok=True)


def _validate_snapshot(destination, snapshot):
    if Path(snapshot.destination) != Path(destination):
        raise ValueError(f'Snapshot destination mismatch: snapshot={snapshot.destination}; requested={destination}')
    if not snapshot._lease.is_file():
        raise ValueError('Snapshot context is closed')


def _read(snapshot, name):
    raw = (snapshot.directory / name).read_bytes()
    entry = next(f for f in snapshot.files if f[0] == name)
    if sha256(raw).hexdigest() != entry[1]:
        raise ValueError('Export file checksum mismatch')
    rows = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
    if len(rows) != entry[2]:
        raise ValueError('Export row count mismatch')
    return rows


def read_current_results(destination, *, snapshot=None):
    if snapshot is None:
        with open_current_snapshot(destination) as current:
            return read_current_results(destination, snapshot=current)
    _validate_snapshot(destination, snapshot)
    rows = _read(snapshot, 'results.jsonl')
    if len(rows) != len(snapshot.results_index):
        raise ValueError('Result identity count mismatch')
    result = []
    for i, (row, identity) in enumerate(zip(rows, snapshot.results_index)):
        _, index, digest, status = identity
        checked = validate_record(row)
        if not checked.valid or index != i or record_digest(row) != digest or row['status'] != status:
            raise ValueError('Invalid published result')
        result.append(checked.record)
    return tuple(result)


def read_frozen_results(path):
    """Read historical fixture archives only; never use this for live outputs."""
    result=[]
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        checked=validate_record(json.loads(line))
        if not checked.valid:raise ValueError('Invalid archived result')
        result.append(checked.record)
    return tuple(result)


def read_current_warnings_by_severity(destination, *, snapshot=None):
    if snapshot is None:
        with open_current_snapshot(destination) as current:
            return read_current_warnings_by_severity(destination, snapshot=current)
    _validate_snapshot(destination, snapshot)
    rows = _read(snapshot, 'warnings_by_severity.jsonl')
    if len(rows) != len(snapshot.results_index):
        raise ValueError('Severity identity count mismatch')
    result = []
    for row, identity in zip(rows, snapshot.results_index):
        pid, i, digest, status = identity
        if (row['paper_id'], row['result_index'], row['result_sha256'], row['status']) != (pid, i, digest, status):
            raise ValueError('Severity identity mismatch')
        if any(type(row[key]) is not list or any(type(v) is not str for v in row[key]) for key in ('informational', 'blocking')):
            raise ValueError('Invalid severity messages')
        result.append(WarningsBySeverityRecord(pid, i, digest, ResultStatus(status), tuple(row['informational']), tuple(row['blocking'])))
    return tuple(result)


def read_current_failures(destination, *, snapshot=None):
    from .jsonl import parse_failure_line
    if snapshot is None:
        with open_current_snapshot(destination) as current:
            return read_current_failures(destination, snapshot=current)
    _validate_snapshot(destination, snapshot)
    return tuple(parse_failure_line(r) for r in _read(snapshot, 'failures.jsonl'))


def read_current_review(destination, *, snapshot=None):
    if snapshot is None:
        with open_current_snapshot(destination) as current:
            return read_current_review(destination, snapshot=current)
    _validate_snapshot(destination, snapshot)
    return tuple(_read(snapshot, 'review.jsonl'))


def prune_versions(destination, *, keep=3):
    if type(keep) is not int or keep < 1:
        raise ValueError('keep must be a positive integer')
    destination = Path(destination)
    removed = []
    with _lock(destination):
        current = json.loads((destination / 'CURRENT').read_text())['version_id']
        leased = {json.loads(p.read_text())['version_id'] for p in (destination / '.leases').glob('*.json')}
        versions = sorted((p for p in (destination / 'versions').iterdir() if p.is_dir() and not p.name.startswith('.')), reverse=True)
        protected = {p.name for p in versions[:keep]} | {current} | leased
        for path in versions:
            if path.name not in protected:
                shutil.rmtree(path); removed.append(path.name)
    return tuple(removed)
