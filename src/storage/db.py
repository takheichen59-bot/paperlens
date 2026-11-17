"""SQLite connections, atomic migrations and nested transaction boundaries."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sqlite3
from contracts import (ContractError, ErrorKind, Stage, PaperMeta, Source,
                       TaskRecord, StageStatus, ExtractionResult, ResultStatus)


def storage_error(exc):
    return ContractError.from_exception(exc, stage=Stage.STORAGE,
                                       error_kind=ErrorKind.VALIDATION_FAILED,retryable=False)


def timestamp(value=None):
    value=value if value is not None else datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Timestamp requires timezone')
    return value.astimezone(timezone.utc).isoformat()


def _paper(row):
    if row is None:return None
    return PaperMeta.model_validate_json(json.dumps({k:row[k] for k in PaperMeta.model_fields})),Source(row['source'])


def _task(row):
    if row is None:return None
    data={k:row[k] for k in TaskRecord.model_fields if k!='error'}
    data['error']=row['error_kind']
    return TaskRecord.model_validate_json(json.dumps(data))


def _result(row):
    if row is None:return None
    return ExtractionResult.model_validate_json(row['payload_json']),ResultStatus(row['status'])


def _error(row):
    if row is None:return None
    return ContractError(Stage(row['stage']),ErrorKind(row['error_kind']),bool(row['retryable']),row['safe_message'])


def migration_statements(text):
    # Preserve quoted text, remove only line comments, reject ambiguous formats.
    cleaned=[];quote=None;i=0
    while i<len(text):
        c=text[i]
        if quote:
            if c==';':raise ValueError('Semicolon inside quoted text forbidden')
            cleaned.append(c)
            if c==quote:
                if i+1<len(text) and text[i+1]==quote:
                    cleaned.append(text[i+1]);i+=1
                else:quote=None
        elif text.startswith('--',i):
            end=text.find('\n',i)
            if end<0:break
            cleaned.append('\n');i=end
        elif text.startswith('/*',i) or text.startswith('*/',i):
            raise ValueError('Block comments forbidden')
        elif c in "'\"`":quote=c;cleaned.append(c)
        elif c=='[':raise ValueError('Bracket quoted identifiers unsupported')
        else:
            if c==';' and (i+1>=len(text) or text[i+1]!='\n'):
                raise ValueError('Statement must end with semicolon-newline')
            cleaned.append(c)
        i+=1
    if quote:raise ValueError('Unterminated quote')
    text=''.join(cleaned)
    parts=text.split(';\n')
    if parts[-1].strip():raise ValueError('Missing statement terminator')
    statements=[]
    for part in parts[:-1]:
        if not part.strip():raise ValueError('Empty SQL statement')
        first=re.match(r'\s*([A-Za-z]+)',part)
        # DDL/data changes only; migrations never manage connections or transactions.
        if not first or first[1].upper() not in {'CREATE','ALTER','DROP','INSERT','UPDATE','DELETE'}:
            raise ValueError('Forbidden migration statement')
        if re.match(r'\s*CREATE\s+(?:TEMP(?:ORARY)?\s+)?TRIGGER\b',part,re.I):
            raise ValueError('Triggers forbidden')
        statements.append(part.strip())
    return tuple(statements)


class Database:
    def __init__(self,path,*,auto_migrate=True,busy_timeout_ms=5000):
        self._depth=0;self._counter=0;self.connection=None
        try:
            if type(busy_timeout_ms) is not int or busy_timeout_ms<0:raise ValueError('Invalid timeout')
            self.connection=sqlite3.connect(str(path),isolation_level=None)
            self.connection.row_factory=sqlite3.Row
            self.connection.execute('PRAGMA foreign_keys=ON')
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute(f'PRAGMA busy_timeout={busy_timeout_ms}')
            if auto_migrate:self.migrate()
        except Exception as exc:
            if self.connection:self.connection.close()
            if isinstance(exc,ContractError):raise
            raise storage_error(exc) from exc

    @property
    def user_version(self):
        try:return self.connection.execute('PRAGMA user_version').fetchone()[0]
        except sqlite3.Error as exc:raise storage_error(exc) from exc

    @contextmanager
    def transaction(self):
        nested=self._depth>0;self._counter+=1;savepoint=f'sp_{self._counter}'
        try:self.connection.execute(f'SAVEPOINT {savepoint}' if nested else 'BEGIN')
        except sqlite3.Error as exc:raise storage_error(exc) from exc
        self._depth+=1
        try:
            yield self
            self.connection.execute(f'RELEASE SAVEPOINT {savepoint}' if nested else 'COMMIT')
        except BaseException as exc:
            try:
                if nested:
                    self.connection.execute(f'ROLLBACK TO SAVEPOINT {savepoint}')
                    self.connection.execute(f'RELEASE SAVEPOINT {savepoint}')
                else:self.connection.execute('ROLLBACK')
            except sqlite3.Error as rollback_error:
                raise storage_error(rollback_error) from rollback_error
            if isinstance(exc,sqlite3.Error):raise storage_error(exc) from exc
            raise
        finally:self._depth-=1

    def migrate(self,*,migrations_dir=None):
        try:
            if self._depth or self.connection.in_transaction:raise ValueError('Migration inside transaction forbidden')
            folder=Path(migrations_dir) if migrations_dir is not None else Path(__file__).parent/'migrations'
            files=sorted(folder.glob('*.sql'))
            numbers=[]
            for p in files:
                m=re.fullmatch(r'(\d{4})_[a-z0-9_]+\.sql',p.name)
                if not m:raise ValueError('Invalid migration filename')
                numbers.append(int(m[1]))
            if not files or numbers!=list(range(1,len(files)+1)):raise ValueError('Missing or duplicate migration')
            current=self.user_version
            if current>len(files):raise ValueError('Unsupported database version')
            for number,path in zip(numbers,files):
                if number<=current:continue
                statements=migration_statements(path.read_text(encoding='utf-8'))
                with self.transaction():
                    for statement in statements:self.connection.execute(statement)
                    self.connection.execute(f'PRAGMA user_version={number}')
        except Exception as exc:
            if isinstance(exc,ContractError):raise
            raise storage_error(exc) from exc

    def close(self):
        try:self.connection.close()
        except sqlite3.Error as exc:raise storage_error(exc) from exc
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
