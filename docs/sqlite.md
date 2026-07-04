# SQLite table definition

`stats/transcribe_runs.sqlite3` に保存する実行台帳の定義。

対象テーブルは `transcribe_runs`。  
1回の文字起こし実行につき、1レコードを追加する。

---

## Table

```text
transcribe_runs
```

---

## Column list

| column | type | nullable | description |
|---|---|---:|---|
| `id` | `INTEGER` | no | SQLite内部の連番ID。`PRIMARY KEY AUTOINCREMENT`。 |
| `run_id` | `TEXT` | yes | run単位の人間向けID。形式は `YYYYMMDD_HHMMSS_{run_label}_{audio_stem}`。 |
| `run_user` | `TEXT` | yes | 実行OSユーザ。 |
| `run_host` | `TEXT` | yes | 実行ホスト名。 |
| `run_started_at` | `TEXT` | yes | 実行開始日時。Python側の `datetime.now().isoformat(timespec="seconds")`。 |
| `run_finished_at` | `TEXT` | yes | 実行終了日時。Python側の `datetime.now().isoformat(timespec="seconds")`。 |
| `elapsed_sec` | `REAL` | yes | 実行にかかった秒数。`time.monotonic()` の差分。 |
| `experiment_name` | `TEXT` | yes | 実験全体の名前。比較集計時のグループ名。例: `l0opback_lang_compare`。 |
| `run_label` | `TEXT` | yes | 実行条件ラベル。例: `ja_auto`, `en_specification`。 |
| `config_path` | `TEXT` | yes | 実行時に読んだconfigファイルのパス。 |
| `config_snapshot` | `TEXT` | yes | `output/{run_id}/config_snapshot.toml` のパス。実行時configのコピー。 |
| `audio_path` | `TEXT` | yes | 入力音声ファイルのフルパス。 |
| `audio_file` | `TEXT` | yes | 入力音声ファイル名。例: `l0opback_ja.m4a`。 |
| `audio_stem` | `TEXT` | yes | 入力音声ファイルの拡張子なしファイル名。例: `l0opback_ja`。 |
| `audio_size_bytes` | `INTEGER` | yes | 入力音声ファイルサイズ。単位はbyte。 |
| `audio_mtime` | `TEXT` | yes | 入力音声ファイルの更新日時。 |
| `source_language` | `TEXT` | yes | 元音声の言語ラベル。人間側が指定する分類。`ja`, `en`, `unknown`。 |
| `model` | `TEXT` | yes | Whisperモデル名。例: `medium`, `large-v3`。 |
| `device` | `TEXT` | yes | 実行デバイス。`cuda` または `cpu`。 |
| `compute_type` | `TEXT` | yes | 計算型。例: `float16`, `int8`。 |
| `language_arg` | `TEXT` | yes | Whisperへ渡した言語指定。`auto`, `ja`, `en`。 |
| `detected_language` | `TEXT` | yes | Whisperが検出した言語。例: `ja`, `en`。 |
| `language_probability` | `REAL` | yes | Whisperの言語判定確率。 |
| `duration_sec` | `REAL` | yes | 音声長。単位は秒。 |
| `segment_count` | `INTEGER` | yes | 出力segment数。 |
| `transcript_chars` | `INTEGER` | yes | 文字起こし本文の文字数合計。各segment textの長さを合計した値。 |
| `vad_filter` | `INTEGER` | yes | VADを使ったか。`1=true`, `0=false`。 |
| `beam_size` | `INTEGER` | yes | Whisperの探索幅。 |
| `output_dir` | `TEXT` | yes | runごとの出力ディレクトリ。 |
| `output_txt` | `TEXT` | yes | `transcript.txt` のパス。 |
| `output_srt` | `TEXT` | yes | `transcript.srt` のパス。 |
| `output_json` | `TEXT` | yes | `result.json` のパス。 |
| `log_path` | `TEXT` | yes | 実行ログファイルのパス。 |
| `status` | `TEXT` | yes | 実行状態。現状は成功時に `success`。 |
| `error_message` | `TEXT` | yes | エラー内容。現状は成功時 `NULL`。 |
| `is_deleted` | `INTEGER` | no | 論理削除フラグ。`0=有効`, `1=削除扱い`。デフォルトは `0`。 |
| `deleted_at` | `TEXT` | yes | 論理削除した日時。 |
| `delete_reason` | `TEXT` | yes | 論理削除理由。例: `misrun`, `duplicate`, `test`。 |

---

## Column groups

### 実行識別

```text
id
run_id
run_user
run_host
```

`id` はDB内部の連番。  
`run_id` は人間が読むための実行ID。  
`run_user` と `run_host` は、誰がどの端末で実行したかを見るための監査用項目。

---

### 実行時刻

```text
run_started_at
run_finished_at
elapsed_sec
```

`elapsed_sec` は処理時間比較に使う。  
音声長に対してどの程度の速度で処理できたかを見る場合は、`duration_sec / elapsed_sec` を計算する。

---

### 実験条件

```text
experiment_name
run_label
config_path
config_snapshot
```

`experiment_name` は実験全体の名前。  
`run_label` は1条件の名前。  
`config_snapshot` は実行時設定を固定保存するためのパス。

---

### 入力音声

```text
audio_path
audio_file
audio_stem
audio_size_bytes
audio_mtime
source_language
```

`source_language` はWhisperの判定結果ではなく、人間が指定する分類。  
`detected_language` と比較することで、auto判定が外れたか確認できる。

---

### Whisper実行条件

```text
model
device
compute_type
language_arg
vad_filter
beam_size
```

`language_arg` はWhisperへ渡した言語指定。  
`source_language` とは別物。

---

### Whisper結果

```text
detected_language
language_probability
duration_sec
segment_count
transcript_chars
```

`segment_count` と `transcript_chars` は軽量な比較指標。  
文字起こし品質そのものを見るには `transcript.txt` のdiffや固有語チェックが必要。

---

### 出力ファイル

```text
output_dir
output_txt
output_srt
output_json
log_path
```

runごとの成果物とログへの参照。  
実体ファイルはGitに載せない。

---

### 状態管理

```text
status
error_message
is_deleted
deleted_at
delete_reason
```

失敗runや重複runは物理削除せず、`is_deleted = 1` にする。  
通常の確認SQLでは `coalesce(is_deleted, 0) = 0` で有効runだけを見る。

---

## CREATE TABLE

現行スクリプトでは、Python側の `init_db()` が以下相当のテーブルを作る。

```sql
CREATE TABLE IF NOT EXISTS transcribe_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    run_id TEXT,
    run_user TEXT,
    run_host TEXT,

    run_started_at TEXT,
    run_finished_at TEXT,
    elapsed_sec REAL,

    experiment_name TEXT,
    run_label TEXT,

    config_path TEXT,
    config_snapshot TEXT,

    audio_path TEXT,
    audio_file TEXT,
    audio_stem TEXT,
    audio_size_bytes INTEGER,
    audio_mtime TEXT,
    source_language TEXT,

    model TEXT,
    device TEXT,
    compute_type TEXT,
    language_arg TEXT,
    detected_language TEXT,
    language_probability REAL,

    duration_sec REAL,
    segment_count INTEGER,
    transcript_chars INTEGER,

    vad_filter INTEGER,
    beam_size INTEGER,

    output_dir TEXT,
    output_txt TEXT,
    output_srt TEXT,
    output_json TEXT,
    log_path TEXT,

    status TEXT,
    error_message TEXT,

    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    delete_reason TEXT
);
```

---

## Indexes

現行スクリプトでは以下のindexを作る。

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_transcribe_runs_run_id
ON transcribe_runs (run_id)
WHERE run_id IS NOT NULL;
```

`run_id` の重複防止用。  
秒timestamp + run_label + audio_stem の衝突防止。

```sql
CREATE INDEX IF NOT EXISTS idx_transcribe_runs_experiment
ON transcribe_runs (experiment_name, run_label);
```

実験名・条件ラベルで集計するためのindex。

```sql
CREATE INDEX IF NOT EXISTS idx_transcribe_runs_audio_language
ON transcribe_runs (audio_file, source_language, language_arg);
```

音声ファイル・元言語・Whisper言語指定で比較するためのindex。

```sql
CREATE INDEX IF NOT EXISTS idx_transcribe_runs_user_host
ON transcribe_runs (run_user, run_host);
```

実行ユーザ・実行ホストで確認するためのindex。

```sql
CREATE INDEX IF NOT EXISTS idx_transcribe_runs_deleted
ON transcribe_runs (is_deleted);
```

論理削除フラグで絞り込むためのindex。

---

## Common queries

有効runだけ見る。

```sql
select
  id,
  run_id,
  run_user,
  run_host,
  run_label,
  audio_file,
  source_language,
  language_arg,
  detected_language,
  round(language_probability, 4) as lang_prob,
  round(duration_sec, 2) as duration,
  round(elapsed_sec, 2) as elapsed,
  segment_count,
  transcript_chars,
  output_dir
from transcribe_runs
where coalesce(is_deleted, 0) = 0
order by id;
```

論理削除済みも含めて見る。

```sql
select
  id,
  coalesce(is_deleted, 0) as is_deleted,
  deleted_at,
  delete_reason,
  run_id,
  run_user,
  run_host,
  run_label,
  audio_file,
  source_language,
  language_arg,
  detected_language,
  round(language_probability, 4) as lang_prob,
  round(duration_sec, 2) as duration,
  round(elapsed_sec, 2) as elapsed,
  segment_count,
  transcript_chars,
  output_dir
from transcribe_runs
order by id;
```

比較集計。

```sql
select
  experiment_name,
  source_language,
  language_arg,
  detected_language,
  round(avg(language_probability), 4) as avg_lang_prob,
  round(avg(elapsed_sec), 2) as avg_elapsed,
  round(avg(segment_count), 1) as avg_segments,
  round(avg(transcript_chars), 1) as avg_chars,
  count(*) as run_count
from transcribe_runs
where coalesce(is_deleted, 0) = 0
group by
  experiment_name,
  source_language,
  language_arg,
  detected_language
order by
  experiment_name,
  source_language,
  language_arg,
  detected_language;
```

model比較集計。

```sql
select
  experiment_name,
  source_language,
  model,
  language_arg,
  detected_language,
  round(avg(language_probability), 4) as avg_lang_prob,
  round(avg(duration_sec), 2) as avg_duration,
  round(avg(elapsed_sec), 2) as avg_elapsed,
  round(avg(duration_sec / elapsed_sec), 2) as realtime_factor,
  round(avg(segment_count), 1) as avg_segments,
  round(avg(transcript_chars), 1) as avg_chars,
  count(*) as run_count
from transcribe_runs
where coalesce(is_deleted, 0) = 0
group by
  experiment_name,
  source_language,
  model,
  language_arg,
  detected_language
order by
  experiment_name,
  source_language,
  model,
  language_arg;
```

実行ユーザ別に見る。

```sql
select
  run_user,
  run_host,
  count(*) as run_count,
  round(avg(elapsed_sec), 2) as avg_elapsed
from transcribe_runs
where coalesce(is_deleted, 0) = 0
group by
  run_user,
  run_host
order by
  run_user,
  run_host;
```

---

## Notes

### 既存DBの古いレコード

`run_user` / `run_host` を追加する前のレコードでは、この2列が `NULL` になる。  
新しいスクリプトで実行したrunから値が入る。

### SQLiteの型

SQLiteは型が緩い。  
このツールでは、日時は `TEXT`、真偽値は `INTEGER`、秒数や確率は `REAL` として保存する。

### 物理削除と論理削除

運用上は物理削除ではなく論理削除を使う。

```sql
update transcribe_runs
set
  is_deleted = 1,
  deleted_at = datetime('now', 'localtime'),
  delete_reason = 'misrun'
where id = 1;
```

通常の確認・集計では以下を条件に入れる。

```sql
where coalesce(is_deleted, 0) = 0
```
