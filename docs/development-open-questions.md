# Development open questions

SAALCO v1.0 は、実装指示書の暫定解釈に従って実装している。以下は規則・仕様レベルの未決事項であり、判定できないものを黙って PASS として扱うことはしない。

分類は実装指示書 §22 に従う（A：実装の細部、B：仕様の曖昧さ、C：規則との衝突、D：本指示書の欠陥）。

## Open

- C / I-1：Evidence は対象 commit と同じ commit には保存できない。対象 commit から HEAD までの変更が `evidence/`・`docs/trace/`・`docs/ids.ledger` に限られる場合だけ、その Evidence を current とみなす。
- C / I-2：検査を、テスト前の `check` とテスト後の `check --verification` の2段に分ける。
- C / I-3：廃止したIDが再利用されないよう、`docs/ids.ledger` を採番の正本とする。
- C / I-4：current な手動 ST の結果で、要件の検証充足を満たせるものとする。
- C / I-5：例外を機械可読にするため、逸脱記録を構造化した `DEV-nnnn` 項目とする。
- C / I-6：実装と設計の差分は `45-implementation-diff.md` に置く。
- C / I-7：Tier の宣言（`00-meta.md`）は、H3 で詳細設計と一緒に承認する。
- C / I-8：`saal` と `saalco` は同じ CLI を起動する。
- B：pytest の終了コードだけでは、parametrize の個々のケースの結果が分からない。テストごとの結果は junitxml から取得し、全ケースが PASS したときだけ PASS とする。結果が得られないテストは `NOT_EVALUATED` とする。
- D：coverage JSON だけでは、全ての実装行とテストを確実に対応付けられるとは限らない。coverage context が得られない場合は `NOT_EVALUATED` とし、PASS にはしない。
- B：差分 Coverage の基準点（§15「直前 Evidence」）は、HEAD の祖先にある Evidence のうち、Coverage の結果が PASS のもので最も近いものと解釈する。FAIL や `NOT_EVALUATED` の Evidence は基準点にしないので、`saalco evidence` を再実行しても Coverage の FAIL が PASS に変わることは無い。
- A：coverage.py が実行対象とみなさない変更行（コメント、空行）は、差分 Coverage 100% として扱う。行の削除だけの変更は「変更行」に数えない。
- B：DEV による例外（§8.6）は、規則番号と scope のトークンの完全一致で照合する。scope のトークンは Feature ID、項目 ID、パスの前方一致のいずれかである。DEV の `rule:` にはカンマ区切りで複数の規則番号を書ける。照合に使う規則番号は、6.4（verifies テストが PASS していない）、6.8（RTM が verified でない）、7.1（ゲートの FAIL / ERROR）、7.3（Coverage）、4.6（未承認の設計に対応する実装）である。
- A：`uv run` の中でツールが見つからない場合（例：プロジェクトの venv に pytest が無い）は、ERROR ではなく FAIL として記録する。どちらも PASS ではない。
- A：`tests/fixtures/` 以下はサンプルデータであり、マーカーの走査と pytest の収集の対象から外す。
- A：Python 3.12 以降で coverage.py が既定で使う `sysmon` 方式は、1行につき最初に実行したテストの測定コンテキストしか記録しない。これでは、未承認の設計に対応する実装の検査（§13-14）で verifies テストを見落とす。そのため `saalco evidence` はテストの実行時に `COVERAGE_CORE=ctrace` を指定する。
- B（未決、2026-09-27 に記録）：`tests/integration/` にテストが1件も無いと、`test.integration`（既定値 `uv run pytest tests/integration`）は pytest の終了コード 5（テストが無い）で終わり、ゲートが FAIL になる。結合テスト仕様が不要な Tier S だけのプロジェクトでは必ず起きる。現状の回避策は、`docs/project.md` の `test.integration:` を空にして `NOT_CONFIGURED` にすることである（`docs/manual.md` 4.8 に記載）。ツール側で終了コード 5 を「対象なし」として扱うべきかは決まっていない。扱う場合は、それを PASS・FAIL・`NOT_CONFIGURED` とは別の結果にするか、Tier M/L の Feature があるのに結合テストが無い状態をどう検出するかも決める必要がある。2026-09-27、`docs/manual.md` を書くために作ったデモプロジェクト（Tier S）で見つかった。今回は実装しない。
- B（未決、2026-09-27 に記録）：`saalco init` が生成する `pyproject.toml` に、最初から `[tool.coverage.run]` の `patch = ["subprocess"]` を入れるべきかは決まっていない。この設定が無いと、E2E テストがサブプロセスとして起動した CLI の実行行が Coverage に数えられない。デモプロジェクトでは、設定する前は全体 Coverage が 55.56% で FAIL になり、設定した後は 100% で PASS になった。入れる場合は、この設定が coverage.py 7.10 以降を前提とすることと、依存の下限をどう扱うかも決める必要がある。今回は実装しない。
  - あわせて確認した結果：SAALCO 自身は、すでに `pyproject.toml` に `patch = ["subprocess"]` を設定している。それでも `saalco check --verification`（2026-09-27、current Evidence は commit `ef63d80`）は、`src/saalco/__init__.py`・`src/saalco/__main__.py`・`src/saalco/errors.py` の3件について「reached by no verifies test」の WARNING を出す。依頼時の「4件」は、同じ出力の WARNING 5件（この3件と、`gate.04.secret_scan`・`gate.05.dependency_audit` の `NOT_CONFIGURED` 2件）とは一致しない。Coverage の JSON を見ると、3ファイルとも全行が実行されているが、測定コンテキストは空文字（`''`）しか記録されていない。モジュールを import した時点で実行される行（`__init__.py` と `errors.py`）は、どのテストの測定コンテキストにも入らない。`__main__.py` は `python -m saalco` のサブプロセスでしか実行されず、pytest-cov のテストごとの測定コンテキストはサブプロセスに引き継がれない。したがって、この3件の WARNING は `patch = ["subprocess"]` では解消しない。
- C（未決、2026-09-27 に記録、判断者：三浦）：`README.md` と `docs/manual.md` を、変更しても Evidence が current のまま扱われるパス（I-1 の例外：現在は `evidence/`・`docs/trace/`・`docs/ids.ledger`）に加えるかは決まっていない。加えない場合、利用者向けの文書を直すたびに Evidence を取り直す必要がある（2026-09-27 の README 日本語化とマニュアル追加で起きた）。加える場合、これらのパスは品質ゲートやテストの結果に影響しない一方で、例外の範囲が広がるほど「Evidence が HEAD のコードを検証した」という主張の範囲を個別に説明する必要が出てくる。個別のファイル名で指定するか、`docs/` 以下の規則管理外の文書をまとめて指定するかも選択肢である。判断は人間（三浦）が行う。

- 2026-11-01：上の未決事項のうち3件（`tests/integration/` が空のときの終了コード5、`init` の `patch = ["subprocess"]`、README・マニュアルを Evidence の例外に加えるか）を、問いカードの紙上試行の対象にした（`docs/questions/`）。2026-11-01、3件ともチャットで回答された（Resolved を参照）。

## Resolved

- 方針決定（2026-11-01、未実装）/ B：上の Open にある3件は、問いカードの紙上試行で人間が次のとおり答えた。いずれも実装はまだで、Open の記録は実装まで残す。(1) `tests/integration/` が空のときの終了コード5は、新しい結果 `NO_TESTS` として記録し、Tier M/L の Feature があれば FAIL、Tier S だけなら FAIL にしない。(2) `saalco init` は `[tool.coverage.run]` に `patch = ["subprocess"]` を書き、dev 依存の coverage の下限を 7.10 にする（既存の `pyproject.toml` は書き換えず案内だけ出す）。(3) `README.md` と `docs/manual.md` の2ファイルを、ファイル名で I-1 の例外に加える。
- 解決済み（2026-09-24）/ D：§9 には「IDを廃止しても台帳の行は消さない」と「台帳と文書の不一致は ERROR」の両方が書かれており、IDを廃止する手段が無かった。実装指示書を改訂版 r3 に改め、台帳の行に `status`（`active` / `retired`）と任意項目 `reason`・`superseded_by` を追加して解決した。`retired` のIDは不一致検査から外し、番号の再利用と、廃止したIDへの参照の残存は ERROR とする。`status` の列が無い既存の行は `active` として従来どおり扱う。
- 解決済み（2026-09-25）/ B：`uv.lock` が無いプロジェクトで `saalco evidence` を実行すると、Evidence の途中で実行する `uv run`（テストと `coverage json`）が `uv.lock` を新しく作る。`uv.lock` は I-1 で差分として許される範囲（`evidence/`・`docs/trace/`・`docs/ids.ledger`）に入らないため、その Evidence は以後 current と扱われない。2026-09-25、F-002 の Specification-derived Test の作成中に見つかった（テスト側では、最初の commit の前に `uv lock` を実行して回避している）。2026-09-25、人間が B 案（`uv.lock` が無い・古い場合は止めて `uv lock` を案内し、`uv run --locked` を使う）を選んだ。 F-003（REQ-0006・AD-0002・DD-0006）で対応した。`language: python` のプロジェクトでは、`uv.lock` が無い・Git 管理されていない・更新が必要な場合に、`saalco evidence` は Evidence を取らずに exit 2 で止まる。`uv run` で始まるコマンドは `--locked` を付けて実行する。`saalco init` は `uv.lock` が無ければ案内を出す。
