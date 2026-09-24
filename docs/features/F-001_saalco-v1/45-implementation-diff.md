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

## Designed but not implemented

- パッケージ構成が、§6 で推奨されているサブパッケージ構成と異なる（モジュールはフラットに置いている。CLI 層とドメインロジックは分離している）。
- ネットワークが原因のゲートの失敗を、通常の FAIL と区別していない（§16 は ERROR を求めている）。
- IDの廃止を行うコマンドが無い。仕様 r3 の §9 に従い、台帳の行に `status` 以降の列を手で追記する。
