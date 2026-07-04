# mojiokoshi

`faster-whisper` を使って音声ファイルを文字起こしするローカル用ツール。

入力音声は `data/` に置く。  
出力は run ごとに `output/{run_id}/` にまとめる。  
実行ログは `log/{run_id}.log` に出す。  
実行結果の統計は `stats/transcribe_runs.sqlite3` に記録する。

---

## 最短セットアップ

WSL Ubuntu想定。

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg sqlite3

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install faster-whisper
```

CUDAで使う場合。

```bash
pip install -U nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12
```

CUDAライブラリにPATHを通す。

```bash
SITE_PACKAGES=$(python -c 'import site; print(site.getsitepackages()[0])')

export LD_LIBRARY_PATH="$SITE_PACKAGES/nvidia/cublas/lib:$SITE_PACKAGES/nvidia/cudnn/lib:$SITE_PACKAGES/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH"
```

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

---

## config.toml 作成

`config.example.toml` をコピーして作る。

```bash
cp config.example.toml config.toml
```

最小例。

```toml
audio_file = "l0opback_ja.m4a"

data_dir = "data"
output_dir = "output"
log_dir = "log"
stats_dir = "stats"
db_file = "transcribe_runs.sqlite3"

experiment_name = "l0opback_lang_compare"
run_label = "ja_auto"
source_language = "ja"

model = "medium"
device = "cuda"
compute_type = "float16"

language = "auto"

beam_size = 5
vad_filter = true
```

各パラメータの詳細は [`docs/config.md`](docs/config.md) を参照。

---

## 複数config

複数条件を回す場合は `configs/` に設定ファイルを分けて置く。

```bash
python transcribe_m4a.py --config configs/ja_auto.toml
python transcribe_m4a.py --config configs/ja_specification.toml
python transcribe_m4a.py --config configs/en_auto.toml
python transcribe_m4a.py --config configs/en_specification.toml

```

---

## 最短実行

### 単発実行

```bash
source .venv/bin/activate
python transcribe_m4a.py
```

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
```

コマンド集は [`docs/commands.md`](docs/commands.md) を参照。

---

## ディレクトリ構成

```text
mojiokoshi/
  transcribe_m4a.py
  config.toml
  config.example.toml
  .gitignore
  README.md
  requirements.txt

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
      check_all.sql

  scripts/
    init_dirs.sh
    run_all.sh
    check.sh
    compare.sh
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
config.example.toml
.gitignore
README.md
docs/**/*.md
query/**/*.sql
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
