CREATE TABLE papers (
 paper_id TEXT PRIMARY KEY NOT NULL, source TEXT NOT NULL, source_id TEXT NOT NULL,
 doi TEXT, title TEXT NOT NULL, page_url TEXT NOT NULL, pdf_url TEXT NOT NULL,
 version TEXT, fetched_at TEXT NOT NULL, UNIQUE(source,source_id)
);
CREATE TABLE tasks (
 task_id TEXT PRIMARY KEY NOT NULL, paper_id TEXT NOT NULL REFERENCES papers(paper_id),
 stage TEXT NOT NULL CHECK(stage IN ('search','metadata','download','parse','extract','validate','export','storage')),
 stage_status TEXT NOT NULL CHECK(stage_status IN ('pending','running','success','failed','skipped')),
 attempts INTEGER NOT NULL CHECK(attempts>=0), config_fingerprint TEXT NOT NULL,
 started_at TEXT, finished_at TEXT, error_kind TEXT CHECK(error_kind IS NULL OR error_kind IN ('not_found','ambiguous_input','rate_limited','network_timeout','invalid_download','pdf_corrupted','needs_ocr','parse_failed','extract_failed','validation_failed','unknown')),
 error_safe_message TEXT, UNIQUE(paper_id,stage),
 CHECK((error_kind IS NULL AND error_safe_message IS NULL) OR (error_kind IS NOT NULL AND error_safe_message IS NOT NULL))
);
CREATE TABLE stage_runs (
 run_id TEXT PRIMARY KEY NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(task_id),
 stage TEXT NOT NULL CHECK(stage IN ('search','metadata','download','parse','extract','validate','export','storage')), status TEXT NOT NULL CHECK(status IN ('pending','running','success','failed','skipped')),
 started_at TEXT, finished_at TEXT
);
CREATE TABLE extraction_results (
 result_id TEXT PRIMARY KEY NOT NULL, paper_id TEXT NOT NULL REFERENCES papers(paper_id),
 extraction_method TEXT NOT NULL, payload_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('success','partial','failed')), updated_at TEXT NOT NULL,
 UNIQUE(paper_id,extraction_method)
);
CREATE TABLE error_events (
 event_id TEXT PRIMARY KEY NOT NULL, paper_id TEXT REFERENCES papers(paper_id),
 stage TEXT NOT NULL CHECK(stage IN ('search','metadata','download','parse','extract','validate','export','storage')), error_kind TEXT NOT NULL CHECK(error_kind IN ('not_found','ambiguous_input','rate_limited','network_timeout','invalid_download','pdf_corrupted','needs_ocr','parse_failed','extract_failed','validation_failed','unknown')),
 retryable INTEGER NOT NULL CHECK(retryable IN (0,1)), safe_message TEXT NOT NULL, created_at TEXT NOT NULL
);
