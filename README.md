# mojiokoshi

`faster-whisper` を使って音声ファイルを文字起こしするローカル用ツール。

入力音声は `data/` に置く。  
出力は run ごとに `output/{run_id}/` にまとめる。  
実行ログは `log/{run_id}.log` に出す。  
実行結果の統計は `stats/transcribe_runs.sqlite3` に記録する。

実行台帳には `run_id`, `run_user`, `run_host`, `app_version`, config、音声ファイル、出力先、ログパス、処理時間、検出言語などを記録する。

---

## 公開スタンス / License

このツールの主目的は作者自身のローカル文字起こし・学習補助。

外部公開する場合も、教育サービス・法人向け製品・サポート付きソフトウェアではなく、個人開発ツールをAS-ISで公開する位置づけとする。

- mojiokoshi本体のlicenseは [`LICENSE`](LICENSE) を参照
- third-party noticeは [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) を参照
- 無保証
- 自己責任
- 原則サポートなし
- 組織端末での実行可否は各組織のルールに従う
- 未署名exe、EDR、AppLocker、WDAC、SmartScreen等による実行制限への対応保証はしない
- NotebookLM等の外部サービスの出力品質や教育的妥当性は本ツールの責任範囲外

versionは [`version.py`](version.py) の `__version__` を単一sourceとする。GitHub Releaseを作る場合は、`__version__ = "0.1.0"` と tag / release名 `v0.1.0` を一致させる。

将来portable zipを作る場合も、初期方針ではCUDA DLLを同梱しない。GPU/CUDA利用者は自分の環境側でCUDAを用意する。

---

## 最短セットアップ

WSL Ubuntu想定。

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg sqlite3

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```

CPU実行だけならここまででよい。

GPU/CUDAを使う端末だけ、追加で入れる。

```bash
pip install -r requirements-cuda.txt
```

CUDAライブラリは、`device = "cuda"` のconfigを `scripts/run_one.sh` / `run_one.py` / `scripts/run_all.sh` から実行した時だけ読み込む。CPU実行時はCUDA環境を読まない。

`run_one.py` はCUDA用の環境変数をPython側で組み立て、子プロセスへ `env` として渡す。`scripts/cuda_env.sh` は手動確認・デバッグ用として当面残す。

CUDAロード確認。

```bash
bash scripts/cuda_env.sh
```

---

## config.toml 作成

`config.example.toml` をコピーして作る。

```bash
cp config.example.toml config.toml
```

`config.example.toml` はCPUでも動く安全側の初期値。

```toml
audio_file = ""

data_dir = "data"
output_dir = "output"
log_dir = "log"
stats_dir = "stats"
db_file = "transcribe_runs.sqlite3"

experiment_name = "example"
run_label = "example_run"
source_language = "unknown"

model = "medium"
device = "cpu"
compute_type = "int8"

language = "auto"

beam_size = 5
vad_filter = true
```

GPU/CUDAを使う場合は、config側で明示する。

```toml
model = "large-v3"
device = "cuda"
compute_type = "float16"
```

各パラメータの詳細は [`docs/config.md`](docs/config.md) を参照。

---

## 複数config

複数条件を回す場合は `configs/` に設定ファイルを分けて置く。

```bash
bash scripts/run_one.sh configs/ja_auto.toml
bash scripts/run_one.sh configs/ja_specification.toml
bash scripts/run_one.sh configs/en_auto.toml
bash scripts/run_one.sh configs/en_specification.toml
```

`config.toml` は手元作業用。  
`configs/*.toml` は再実行可能な実験条件としてGitに載せる。

---

## 最短実行

### 単発実行

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

結果確認。

```bash
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check.sql
```

### 複数条件をまとめて実行

```bash
bash scripts/run_all.sh
```

### 結果確認

```bash
bash scripts/check.sh
bash scripts/compare.sh
bash scripts/compare_model.sh
```

コマンド集は [`docs/commands.md`](docs/commands.md) を参照。

---

## ディレクトリ構成

```text
mojiokoshi/
  transcribe_m4a.py
  run_one.py
  orchestration.py
  version.py
  config.toml
  config.example.toml
  .gitignore
  LICENSE
  THIRD_PARTY_NOTICES.md
  README.md
  requirements.txt
  requirements-cuda.txt

  configs/
    ja_auto.toml
    ja_specification.toml
    en_auto.toml
    en_specification.toml

  data/
    .gitkeep
    *.m4a

  output/
    .gitkeep
    {run_id}/
      transcript.txt
      transcript.srt
      result.json
      config_snapshot.toml

  log/
    .gitkeep
    {run_id}.log

  stats/
    .gitkeep
    transcribe_runs.sqlite3

  query/
    dml/
      check.sql
      compare.sql
      compare_model.sql
      check_all.sql

  scripts/
    init_dirs.sh
    cuda_env.sh
    check_cuda_runtime.py
    run_one.sh
    run_all.sh
    check.sh
    compare.sh
    compare_model.sh
    check_all.sh
    soft_delete.sh
    restore_run.sh
    diff_latest.sh

  docs/
    config.md
    commands.md
    sqlite.md
```

---

## run_id

runごとに以下の形式でIDを発行する。

```text
YYYYMMDD_HHMMSS_{run_label}_{audio_stem}
```

例。

```text
20260704_215405_ja_auto_l0opback_ja
20260704_215620_en_auto_l0opback_en
```

出力先。

```text
output/20260704_215405_ja_auto_l0opback_ja/
  transcript.txt
  transcript.srt
  result.json
  config_snapshot.toml
```

ログ。

```text
log/20260704_215405_ja_auto_l0opback_ja.log
```

この規模では、秒までのtimestampで十分。並列実行なし・手元実験なら衝突はほぼ考えなくてよい。

---

## Git管理方針

Gitに載せるもの。

```text
transcribe_m4a.py
run_one.py
orchestration.py
version.py
requirements.txt
requirements-cuda.txt
config.example.toml
.gitignore
LICENSE
THIRD_PARTY_NOTICES.md
README.md
docs/**/*.md
query/**/*.sql
configs/*.toml
scripts/*.sh
scripts/*.py
data/.gitkeep
output/.gitkeep
log/.gitkeep
stats/.gitkeep
```

Gitに載せないもの。

```text
config.toml
config_*.toml
data/*.m4a
output/*
log/*
stats/*.sqlite3
.venv/
```

---

## よく見るファイル

```text
transcript.txt
  タイムスタンプ付き文字起こし。人間が読む用。

transcript.srt
  字幕ファイル。VLCや動画編集ソフトに読ませる用。

result.json
  後処理用。segments、検出言語、音声長などを含む。

config_snapshot.toml
  実行時configのコピー。あとから条件を確認する用。

log/{run_id}.log
  実行ログ。Tracebackもここに出る。
```

---

## 詳細

- [`docs/config.md`](docs/config.md): `config.toml` のパラメータ説明
- [`docs/commands.md`](docs/commands.md): 実行、確認、diff、論理削除、Git確認のコマンド集
- [`docs/sqlite.md`](docs/sqlite.md): SQLite実行台帳のテーブル定義
