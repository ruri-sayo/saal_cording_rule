---
kind: IMPLEMENTATION_DIFF
feature: F-001
status: draft
---

# Implementation Diff

## Implemented but not designed

- `src/saalco/coverage_contexts.py`：coverage.py の測定コンテキストを読み込むモジュール。RTM の `impl_files` 列と、未承認の設計に対応する実装の検査（§13-14）で使う。30・35 の文書にはまだ記載していない。
- `saalco new --non-interactive` オプション（仕様 §2 では `init` にだけ定義されている）。
- manifest の最上位の `overall` と `coverage.json_path`（§17 の記録項目に無い）。
- 生成する `.gitignore` に、Python のビルド生成物（`__pycache__/`、`*.py[cod]`、`.venv/`、`*.egg-info/`、`.coverage`）も追加する。
- DEV の `rule:` に複数の規則番号をカンマ区切りで書ける。未承認の設計に対応する実装の検査は、規則 4.6 の逸脱として DEV と照合する（§8.6 の拡張。未決事項に記録済み）。
- `saal_rules_version` として 1.0 と 1.1 の両方を受け付ける。`saalco init` は 1.1 を書き込む（規則 1.1 で追加された第11.5項は、SAALCO では検査しない）。
- `saalco retire` の案内メッセージとエラーメッセージは英語で出力する。REQ-0004 の日本語化の対象は生成する文書と `AGENTS.md` の本文であり、CLI の実行時出力は既存のメッセージに合わせて英語のままとした。
- `saalco retire` は、`--superseded-by` に廃止対象と同じIDを指定した場合を拒否しない（DD-0003 に記載が無いため）。

## Notes

- 2026-09-24、Specification-derived Test（`tests/*/test_spec_*.py`）は、実装コードと既存テストを読まない別のエージェントが、承認済み文書と公開インターフェース（シグネチャと docstring のみ）から作成した。並行して実装を担当したエージェントが、`ruff format` の実行で `tests/unit/test_spec_units.py` を一度整形し、すぐに元に戻した。情報の流れは「実装側がテストに触れた」向きであり、テストが実装を写し取るものではないが、独立性が完全ではなかったことをここに記録する。

## Designed but not implemented

- パッケージ構成が、§6 で推奨されているサブパッケージ構成と異なる（モジュールはフラットに置いている。CLI 層とドメインロジックは分離している）。
- ネットワークが原因のゲートの失敗を、通常の FAIL と区別していない（§16 は ERROR を求めている）。
