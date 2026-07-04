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

## install

CPU実行の基本構成。

```bash
pip install -r requirements.txt
```

GPU/CUDAを使う端末だけ追加。

```bash
pip install -r requirements-cuda.txt
```

---

## 実行

通常実行。

```bash
python transcribe_m4a.py
```

`device = "cuda"` のconfigを使う場合は、CUDA環境を自動で読む `scripts/run_one.sh` 経由で実行する。

```bash
bash scripts/run_one.sh configs/ja_auto.toml
```

別configを指定して実行。

```bash
bash scripts/run_one.sh configs/ja_auto.toml
bash scripts/run_one.sh configs/ja_specification.toml
bash scripts/run_one.sh configs/en_auto.toml
bash scripts/run_one.sh configs/en_specification.toml
```

---

## scripts

`scripts/` には、よく使う操作をまとめたshellを置く。

初回またはzip展開後に実行権限を付ける。

```bash
chmod +x scripts/*.sh
```

### directory初期化

```bash
bash scripts/init_dirs.sh
```

作成するもの。

```text
data/
output/
log/
stats/
query/dml/
docs/
configs/
scripts/
```

### CUDA環境確認

`requirements-cuda.txt` を入れた端末で確認する。

```bash
bash scripts/cuda_env.sh
```

CPU実行だけならこの確認は不要。

### config指定で1件実行

```bash
bash scripts/run_one.sh configs/ja_auto.toml
```

`run_one.sh` はconfig内の `device` を見る。

```text
device = "cpu"
  CUDA環境を読まずに実行する

device = "cuda"
  scripts/cuda_env.sh をsourceしてから実行する
```

### 4条件まとめて実行

```bash
bash scripts/run_all.sh
```

実行するconfig。

```text
configs/ja_auto.toml
configs/ja_specification.toml
configs/en_auto.toml
configs/en_specification.toml
```

実行後に以下も表示する。

```text
query/dml/check.sql
query/dml/compare.sql
query/dml/compare_model.sql
```

### 一覧確認

```bash
bash scripts/check.sh
```

中身。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check.sql
```

### 比較集計

```bash
bash scripts/compare.sh
```

中身。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare.sql
```

### model比較集計

```bash
bash scripts/compare_model.sh
```

中身。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare_model.sql
```

### 論理削除済も含めて確認

```bash
bash scripts/check_all.sh
```

中身。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check_all.sql
```

### 論理削除

DB上でrunを除外する。出力ファイルやログは消さない。

DBの`id`で指定する例。

```bash
bash scripts/soft_delete.sh 1 misrun
```

`run_id`で指定する例。

```bash
bash scripts/soft_delete.sh 20260704_214356_ja_specification_l0opback_ja misrun
```

### 論理削除を戻す

DBの`id`で戻す例。

```bash
bash scripts/restore_run.sh 1
```

`run_id`で戻す例。

```bash
bash scripts/restore_run.sh 20260704_214356_ja_specification_l0opback_ja
```

### 最新run同士のdiff

```bash
bash scripts/diff_latest.sh
```

比較する組み合わせ。

```text
ja_specification vs ja_auto
en_specification vs en_auto
```

出力先。

```text
output/diff/{timestamp}_ja_specification_vs_ja_auto.diff
output/diff/{timestamp}_en_specification_vs_en_auto.diff
```

diffが空なら、出力本文は同一。

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

model比較集計。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare_model.sql
```

論理削除済みも含めて確認。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check_all.sql
```

直接SQLを投げる例。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 'select id, run_id, run_user, run_host, language_arg, detected_language, elapsed_sec from transcribe_runs order by id;'
```

---

## query/dml/check.sql

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

---

## query/dml/compare.sql

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

---

## query/dml/compare_model.sql

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

---

## query/dml/check_all.sql

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

---

## 論理削除

失敗runは物理削除せず、SQLite上で論理削除する。

失敗runを論理削除する例。

```bash
bash scripts/soft_delete.sh 1 misrun
```

論理削除を戻す例。

```bash
bash scripts/restore_run.sh 1
```

手でSQLを投げる場合。

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

---

## diff

日本語の言語指定とautoを比較する例。

```bash
diff -u \
  output/20260704_214755_ja_specification_l0opback_ja/transcript.txt \
  output/20260704_215405_ja_auto_l0opback_ja/transcript.txt \
  > output/ja_spec_vs_auto.diff
```

英語の言語指定とautoを比較する例。

```bash
diff -u \
  output/20260704_215154_en_specification_l0opback_en/transcript.txt \
  output/20260704_215620_en_auto_l0opback_en/transcript.txt \
  > output/en_spec_vs_auto.diff
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

## Git確認

Git管理対象。

```bash
git ls-files data log output stats configs scripts docs query
```

期待値の例。

```text
data/.gitkeep
log/.gitkeep
output/.gitkeep
stats/.gitkeep
configs/*.toml
scripts/*.sh
docs/*.md
query/**/*.sql
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
mkdir -p data output log stats query/dml docs configs scripts
touch data/.gitkeep output/.gitkeep log/.gitkeep stats/.gitkeep
```
