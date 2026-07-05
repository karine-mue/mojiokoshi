# diff scripts

文字起こし結果の `transcript.txt` を比較するための補助script。

---

## 同一experiment内の auto / language指定比較

```bash
bash scripts/diff_latest.sh
```

引数なしの場合は、最新の有効runから `experiment_name` を決める。

明示する場合。

```bash
bash scripts/diff_latest.sh l0opback_lang_compare_LargeV3
```

比較対象。

```text
ja_specification vs ja_auto
en_specification vs en_auto
```

出力先。

```text
output/diff/{timestamp}_{experiment_name}_ja_specification_vs_ja_auto.diff
output/diff/{timestamp}_{experiment_name}_en_specification_vs_en_auto.diff
```

このscriptは同一 `experiment_name` 内だけを見る。model差分など、実験をまたぐ比較には使わない。

---

## model差分比較

同じ `source_language` / `language_arg` で、最新のmodel別runを比較する。

```bash
bash scripts/diff_model_latest.sh ja ja medium large-v3
bash scripts/diff_model_latest.sh en en medium large-v3
bash scripts/diff_model_latest.sh en auto medium large-v3
```

experiment名も明示する場合。

```bash
bash scripts/diff_model_latest.sh \
  ja \
  ja \
  l0opback_lang_compare \
  medium \
  l0opback_lang_compare_LargeV3 \
  large-v3
```

出力先。

```text
output/diff/{timestamp}_model_{source_language}_{language_arg}_{left_experiment}_{left_model}_vs_{right_experiment}_{right_model}.diff
```

---

## 共通仕様

- `coalesce(is_deleted, 0) = 0` のrunだけを見る
- `coalesce(status, 'success') = 'success'` のrunだけを見る
- `output_dir/transcript.txt` を比較する
- diffが空なら本文は同一
- `PYTHON=...` でPython interpreterを明示できる

```bash
PYTHON=.venv/bin/python bash scripts/diff_latest.sh l0opback_lang_compare_LargeV3
```
