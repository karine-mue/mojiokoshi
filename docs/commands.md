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

CLI互換入口。

```bash
bash scripts/run_one.sh configs/ja_auto.toml
```

`scripts/run_one.sh` は `.venv/bin/activate` があれば自動でsourceし、`run_one.py` を起動する。

Python入口を直接使う場合。

```bash
python run_one.py configs/ja_auto.toml
```

`device = "cuda"` のconfigを使う場合も、`run_one.py` がCUDA環境を準備してから `transcribe_m4a.py` を子プロセスとして起動する。

別configを指定して実行。

```bash
bash scripts/run_one.sh configs/ja_auto.toml
bash scripts/run_one.sh configs/ja_specification.toml
bash scripts/run_one.sh configs/en_auto.toml
bash scripts/run_one.sh configs/en_specification.toml
```

低レベル入口として `transcribe_m4a.py` を直接実行することもできる。ただし、CUDA環境準備や失敗run記録は `run_one.py` / `scripts/run_one.sh` 側の責務。

```bash
python transcribe_m4a.py
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

`scripts/cuda_env.sh` は手動確認・デバッグ用として当面残す。通常の1件実行では、`run_one.py` がCUDA用の環境変数をPython側で組み立て、子プロセスへ `env` として渡す。

### config指定で1件実行

```bash
bash scripts/run_one.sh configs/ja_auto.toml
```

`run_one.sh` はconfig内の `device` を見る。

```text
device = "cpu"
  CUDA環境を読まずに実行する

device = "cuda"
  Python orchestrationがCUDA環境を作り、子プロセスへenvとして渡す
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

一覧、比較集計、model比較集計、論理削除済み確認は `query/dml/*.sql` を使う。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check.sql
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare.sql
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare_model.sql
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check_all.sql
```

---

## query/dml/check.sql

有効run一覧を見るSQL。

---

## query/dml/compare.sql

実験名、元言語、言語指定、検出言語ごとの比較集計SQL。

---

## query/dml/compare_model.sql

モデル別の処理時間、realtime factor、出力量を見る比較集計SQL。

---

## query/dml/check_all.sql

論理削除済みrunや失敗runも含めて見るSQL。

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
scripts/*.py
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
