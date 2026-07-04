# commands

作業中に使うコマンド集。

---

## venv

venvを有効化。

```bash
source .venv/bin/activate
```

venvを抜ける。

```bash
deactivate
```

---

## 実行

通常実行。

```bash
python transcribe_m4a.py
```

別configを指定して実行。

```bash
python transcribe_m4a.py --config config_en.toml
```

---

## SQLite確認

一覧。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check.sql
```

比較集計。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare.sql
```

論理削除済みも含めて確認。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check_all.sql
```

直接SQLを投げる例。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 'select id, run_id, language_arg, detected_language, elapsed_sec from transcribe_runs order by id;'
```

---

## query/dml/check.sql

```sql
select
  id,
  run_id,
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

---

## query/dml/compare.sql

```sql
select
  source_language,
  language_arg,
  detected_language,
  round(avg(language_probability), 4) as avg_lang_prob,
  round(avg(elapsed_sec), 2) as avg_elapsed,
  round(avg(segment_count), 1) as avg_segments,
  round(avg(transcript_chars), 1) as avg_chars,
  count(*) as run_count
from transcribe_runs
where experiment_name = 'l0opback_lang_compare'
  and coalesce(is_deleted, 0) = 0
group by
  source_language,
  language_arg,
  detected_language
order by
  source_language,
  language_arg,
  detected_language;
```

---

## query/dml/check_all.sql

```sql
select
  id,
  coalesce(is_deleted, 0) as is_deleted,
  deleted_at,
  delete_reason,
  run_id,
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

---

## 論理削除

失敗runは物理削除せず、SQLite上で論理削除する。

初回のみ列追加。

```bash
sqlite3 stats/transcribe_runs.sqlite3 <<'SQL'
alter table transcribe_runs add column is_deleted integer not null default 0;
alter table transcribe_runs add column deleted_at text;
alter table transcribe_runs add column delete_reason text;
SQL
```

失敗runを論理削除する例。

```bash
sqlite3 stats/transcribe_runs.sqlite3 <<'SQL'
update transcribe_runs
set
  is_deleted = 1,
  deleted_at = datetime('now', 'localtime'),
  delete_reason = 'misrun'
where id = 1;
SQL
```

確認。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 'select id, run_id, is_deleted, deleted_at, delete_reason from transcribe_runs order by id;'
```

論理削除を戻す例。

```bash
sqlite3 stats/transcribe_runs.sqlite3 <<'SQL'
update transcribe_runs
set
  is_deleted = 0,
  deleted_at = null,
  delete_reason = null
where id = 1;
SQL
```

---

## diff

日本語の言語指定とautoを比較する例。

```bash
diff -u   output/20260704_214755_ja_specification_l0opback_ja/transcript.txt   output/20260704_215405_ja_auto_l0opback_ja/transcript.txt   > output/ja_spec_vs_auto.diff
```

英語の言語指定とautoを比較する例。

```bash
diff -u   output/20260704_215154_en_specification_l0opback_en/transcript.txt   output/20260704_215620_en_auto_l0opback_en/transcript.txt   > output/en_spec_vs_auto.diff
```

diffが空なら、出力本文は同一。

```bash
ls -lh output/*.diff
```

中身を見る。

```bash
less output/ja_spec_vs_auto.diff
```

---

## 出力確認

runごとの出力一覧。

```bash
find output -maxdepth 2 -type f | sort
```

最新runの出力を見る。

```bash
ls -ltr output | tail
```

ログを見る。

```bash
ls -ltr log | tail
```

最新ログを追う。

```bash
tail -n 80 log/*.log
```

---

## CUDA確認

ロード確認。

```bash
python - <<'PY'
import ctypes

for lib in [
    "libcublas.so.12",
    "libcublasLt.so.12",
    "libcudnn.so.9",
    "libcudart.so.12",
]:
    ctypes.CDLL(lib)
    print("OK", lib)
PY
```

`LD_LIBRARY_PATH` を一時的に通す。

```bash
SITE_PACKAGES=$(python -c 'import site; print(site.getsitepackages()[0])')

export LD_LIBRARY_PATH="$SITE_PACKAGES/nvidia/cublas/lib:$SITE_PACKAGES/nvidia/cudnn/lib:$SITE_PACKAGES/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH"
```

---

## Git確認

Git管理対象。

```bash
git ls-files data log output stats
```

期待値。

```text
data/.gitkeep
log/.gitkeep
output/.gitkeep
stats/.gitkeep
```

ignore確認。

```bash
git status --ignored -s
```

`!!` はignore済み。

```text
!! data/l0opback_ja.m4a
!! output/...
!! log/...
!! stats/transcribe_runs.sqlite3
```

---

## 既存の平置きoutput退避

```bash
mkdir -p output/bk
mv output/2026* output/bk/ 2>/dev/null || true
```

---

## ディレクトリ初期化

```bash
mkdir -p data output log stats query/dml docs
touch data/.gitkeep output/.gitkeep log/.gitkeep stats/.gitkeep
```
