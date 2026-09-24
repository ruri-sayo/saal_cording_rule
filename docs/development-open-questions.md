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

## Resolved

- 解決済み（2026-09-24）/ D：§9 には「IDを廃止しても台帳の行は消さない」と「台帳と文書の不一致は ERROR」の両方が書かれており、IDを廃止する手段が無かった。実装指示書を改訂版 r3 に改め、台帳の行に `status`（`active` / `retired`）と任意項目 `reason`・`superseded_by` を追加して解決した。`retired` のIDは不一致検査から外し、番号の再利用と、廃止したIDへの参照の残存は ERROR とする。`status` の列が無い既存の行は `active` として従来どおり扱う。
