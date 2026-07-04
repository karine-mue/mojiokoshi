# config.toml

`config.toml` は、どの音声を、どのモデル・言語・実験条件で文字起こしするかを決める設定ファイル。

---

## 全体例

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

---

## 入出力まわり

| parameter | example | description |
|---|---|---|
| `audio_file` | `"l0opback_ja.m4a"` | 入力音声ファイル名。`data_dir` 配下から探す。空文字 `""` の場合は、`data_dir` 内で更新日時が最新の音声ファイルを読む。 |
| `data_dir` | `"data"` | 入力音声を置くディレクトリ。 |
| `output_dir` | `"output"` | 文字起こし結果を出すディレクトリ。runごとに `output/{run_id}/` が作られる。 |
| `log_dir` | `"log"` | 実行ログを出すディレクトリ。 |
| `stats_dir` | `"stats"` | SQLiteの実行記録DBを置くディレクトリ。 |
| `db_file` | `"transcribe_runs.sqlite3"` | 実行記録DBのファイル名。 |

`audio_file` を空にした例。

```toml
audio_file = ""
```

この場合、`data/` にある最新の `.m4a`, `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.opus` のどれかが入力になる。

---

## 実験識別まわり

| parameter | example | description |
|---|---|---|
| `experiment_name` | `"l0opback_lang_compare"` | 実験全体の名前。SQLite集計時のグループ名になる。 |
| `run_label` | `"ja_auto"` | 1回のrunにつけるラベル。`run_id` にも入る。 |
| `source_language` | `"ja"` | 元音声の言語ラベル。`ja`, `en`, `unknown` のいずれか。Whisperの判定結果ではなく、人間側が「この音声は何語版か」を記録するための項目。 |

例。

```toml
experiment_name = "l0opback_lang_compare"
run_label = "ja_auto"
source_language = "ja"
```

この場合、run_idはだいたいこうなる。

```text
20260704_215405_ja_auto_l0opback_ja
```

`run_id` の形式。

```text
YYYYMMDD_HHMMSS_{run_label}_{audio_stem}
```

---

## モデル・GPUまわり

| parameter | example | description |
|---|---|---|
| `model` | `"medium"` | Whisperモデルのサイズ。大きいほど認識精度は上がりやすいが、処理時間・VRAM使用量も増える。 |
| `device` | `"cuda"` | 実行デバイス。GPUなら `cuda`、CPUなら `cpu`。 |
| `compute_type` | `"float16"` | 計算時の数値形式。GPUでは `float16`、CPUでは `int8` が使いやすい。空文字にすると `device` に応じて自動設定する。 |

モデル例。

```toml
model = "small"
model = "medium"
model = "large-v3"
```

目安。

| model | speed | note |
|---|---|---|
| `small` | 速い | 試し打ち用。 |
| `medium` | 中間 | NotebookLM音声の通常run用。 |
| `large-v3` | 重い | 固有名詞や崩れた箇所を詰める比較用。 |

GPU実行例。

```toml
device = "cuda"
compute_type = "float16"
```

CPU実行例。

```toml
device = "cpu"
compute_type = "int8"
```

自動設定に任せる例。

```toml
compute_type = ""
```

この場合、スクリプト側で以下になる。

```text
device = "cuda" -> compute_type = "float16"
device = "cpu"  -> compute_type = "int8"
```

---

## 言語まわり

| parameter | example | description |
|---|---|---|
| `language` | `"auto"` | Whisperに渡す認識言語。`auto`, `ja`, `en` のいずれか。 |

例。

```toml
language = "auto"
```

`auto` は音声から言語を自動判定する。  
NotebookLM音声のように冒頭からその言語で話し始めるファイルでは安定しやすい。

```toml
language = "ja"
```

日本語として固定して認識する。

```toml
language = "en"
```

英語として固定して認識する。

注意点。

```text
language = "auto"
  言語判定が外れると、全文がその影響を受ける。

language = "ja" / "en"
  音声の言語が分かっている場合は条件固定しやすい。
  ただし指定を間違えると全文が崩れる。
```

`source_language` と `language` は別物。

```toml
source_language = "ja"
language = "auto"
```

これは「元音声は日本語版として記録するが、Whisperには自動判定させる」という意味。

```toml
source_language = "ja"
language = "ja"
```

これは「元音声は日本語版として記録し、Whisperにも日本語固定で渡す」という意味。

---

## beam_size

| parameter | example | description |
|---|---|---|
| `beam_size` | `5` | Whisperが候補文を探索するときの幅。大きくすると複数候補を比較しながら出力を決める。 |

イメージ。

```text
beam_size = 1
  速い。
  候補探索が浅い。
  文字起こしが軽くなる。

beam_size = 5
  標準的。
  速度と認識結果のバランスが取りやすい。

beam_size = 10
  重くなる。
  多少よくなる場合もあるが、処理時間が増える。
```

通常runではまずこれ。

```toml
beam_size = 5
```

品質比較実験では、`beam_size` を変えると比較条件が増える。  
言語指定あり/なしだけを比べたい場合は、`beam_size = 5` で固定する。

---

## vad_filter

| parameter | example | description |
|---|---|---|
| `vad_filter` | `true` | Voice Activity Detection。発話している区間を検出し、無音・長い間・環境音をある程度除いてから認識する。 |

`true` の場合。

```toml
vad_filter = true
```

```text
長い無音で変な字幕が出にくい。
処理が軽くなりやすい。
普通の会話音声では使いやすい。
```

`false` の場合。

```toml
vad_filter = false
```

```text
無音や間も含めて処理する。
話し始め・話し終わりの欠けを避けたい時に比較しやすい。
声質変化や間の観察では比較用になる。
```

NotebookLM音声の通常文字起こしでは、まずこれ。

```toml
vad_filter = true
```

声質変化や発話境界を詰める比較では、別runでこれを試す。

```toml
vad_filter = false
```

---

## 4条件比較の設定例

日本語音声 × 言語auto。

```toml
audio_file = "l0opback_ja.m4a"
run_label = "ja_auto"
source_language = "ja"
language = "auto"
```

日本語音声 × 言語指定。

```toml
audio_file = "l0opback_ja.m4a"
run_label = "ja_specification"
source_language = "ja"
language = "ja"
```

英語音声 × 言語auto。

```toml
audio_file = "l0opback_en.m4a"
run_label = "en_auto"
source_language = "en"
language = "auto"
```

英語音声 × 言語指定。

```toml
audio_file = "l0opback_en.m4a"
run_label = "en_specification"
source_language = "en"
language = "en"
```

この4条件で比較する場合、以下は固定する。

```toml
model = "medium"
device = "cuda"
compute_type = "float16"
beam_size = 5
vad_filter = true
```

こうすると、差分の主因を `language` の違いに寄せられる。

---

## よく変える項目

通常run。

```toml
audio_file = "l0opback_ja.m4a"
run_label = "ja_auto"
source_language = "ja"
language = "auto"
```

品質を上げたい時。

```toml
model = "large-v3"
```

CPUで逃がす時。

```toml
device = "cpu"
compute_type = "int8"
```

言語判定が怪しい時。

```toml
language = "ja"
```

または、

```toml
language = "en"
```

発話境界を比較したい時。

```toml
vad_filter = false
```
