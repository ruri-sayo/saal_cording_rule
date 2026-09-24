---
kind: REQ
feature: F-001
status: approved
approved_by: ruri-sayo
approved_at: 2026-09-24T18:42:22+09:00
version: 1
approved_hash: 0c26cf771588f432308e51272d2db2f0c3eade7d9b01790d3db3745190655f58
---

# Requirements

### REQ-0001: Operate the SAAL development lifecycle locally

covers: -
verify: test

SAALCO は、SAAL 規則で定義された開発ライフサイクル（init → new → approve → check → trace → evidence）をローカル環境だけで一通り運用できること。次の各項は、個別に検証可能な主張である（実装指示書 §2）。

1. `saalco init [--name N --type research|system --language python|other --spec PATH --non-interactive]` により、標準ディレクトリ構造（`AGENTS.md`、`docs/project.md`、`docs/ids.ledger`、`docs/rules/SAAL-DEV-RULES.md`、`docs/input/`、`docs/architecture/`、`docs/features/`、`docs/trace/`、`evidence/`、`src/`、`tests/unit|integration|e2e/`、`.saal/artifacts/`）を生成できること（実装指示書 §7.1）。
2. `saalco init` は、Git 未初期化であれば `git init` を行い、既存の `.git/`・`src/`・`tests/` を破壊せず、既存ファイルと衝突する場合は上書きせず衝突ファイルを列挙して通知すること（実装指示書 §7.1）。
3. `saalco init` は `--type research` と `--type system` の両方で動作し、生成される `80-outcome.md` のテンプレートが種別に応じて異なること（実装指示書 §7.4、§18）。
4. `saalco init --language other` の場合でも、init と文書管理（`new`・`approve`・`check` の静的検査・`trace`）は動作し、テスト・Coverage の判定は `NOT_EVALUATED` になること（実装指示書 §7.3）。
5. `saalco new feature "Name" --tier S|M|L [--slug SLUG]` により `F-nnn` を採番し、`docs/features/F-nnn_<slug>/00-meta.md` を作成し、Tier に応じて必要な文書をテンプレートから生成すること（実装指示書 §10、規則 2.4）。
6. `saalco new req|ad|dd|md|ut|it|st|dev --feature F-001 "Title"` により、該当種別のIDを台帳経由で採番し、対応する文書が無ければテンプレートから作成し、あれば項目の雛形を追記すること。採番したIDのみを標準出力に返すこと（実装指示書 §9、§10）。
7. `saalco new` が承認済みの文書に項目を追記した場合、その文書の `status` を `draft` に戻し、「承認が無効になった」旨をWARNINGとして表示すること（実装指示書 §10）。
8. `saalco approve <path> [<path> ...]` は、TTY 経由の実行でのみ動作し（`SAALCO_ALLOW_NONTTY_APPROVE=1` を除く）、`status: approved`・`approved_by`・`approved_at`・`approved_hash`・`version` を記録すること（実装指示書 §11）。
9. `saalco check [--verification] [--json]` は、`--verification` を付けない場合は実装指示書 §12 の静的検査項目（ヘッダ形式、Tier宣言、必須文書、ID台帳整合、`covers:`/`verifies` の参照妥当性、承認hash整合、Specification-derived Test の紐付け、UT/MDの網羅、`verify: static` の記載、承認キーの整合）を実行すること。
10. `saalco check --verification` は、§12 の全項目に加え、実装指示書 §13 の検査項目（current Evidence の存在、`verifies` テストのPASS、Coverage基準、未承認の設計に対応する実装、RTM の `verified` 判定、DEV記録による例外、`NOT_CONFIGURED` ゲートのWARNING）を実行すること。
11. `saalco check` は、全ての違反を列挙してから終了し、最初の1件で停止しないこと。最後に `N errors, M warnings` を出力すること（実装指示書 §5）。
12. `saalco trace [--json]` は、`docs/trace/rtm.csv` と `docs/trace/rtm.md` を、同じ入力からは常に同じ内容（タイムスタンプを含まない、ID順にソートされた行）で生成すること（実装指示書 §14）。
13. `saalco evidence` は、作業ツリーがクリーンな場合にのみ実行でき、対象commitに対する `evidence/<commit>/<run-id>/manifest.json` と `summary.md`、`.saal/artifacts/<commit>/<run-id>/` の生データを出力すること。未commitの変更がある場合は拒否すること（実装指示書 §17）。
14. `saalco evidence --package F-001` は、`.saal/packages/F-001/` に `index.md` と `package.json` を生成し、既存の記録を複製せず参照としてまとめること（実装指示書 §17.1）。
15. コマンドの終了コードは、成功時 `0`、検査失敗時 `1`、使い方・設定のエラー時 `2`、環境・外部ツール実行のエラー時 `3` であること（実装指示書 §5）。
16. 判定できない項目（Coverage が計算できない場合、テスト結果が取得できない場合等）は `NOT_EVALUATED` として記録され、`NOT_EVALUATED` が `PASS` として扱われることは無いこと。対応する逸脱記録（DEV）が無い `NOT_EVALUATED` は FAIL として扱われること（実装指示書 §0、§15）。
17. `saal` は `saalco` の別名として登録され、どのサブコマンドでも同一の動作をすること（実装指示書 §1 暫定解釈 I-8、規則 13章冒頭）。

### REQ-0002: Retire IDs without reusing their numbers

covers: -
verify: test

IDを廃止できること。廃止したIDの台帳の行は削除せず、その番号を二度と採番しない。廃止したIDに対応する文書項目が無くても、`saalco check` は台帳と文書の不一致として扱わない。廃止したIDの再利用と、廃止したIDへの参照の残存は `saalco check` がERRORにする（実装指示書 §9、改訂版 r3）。

### REQ-0003: Retire ledger IDs via the CLI

covers: -
verify: test

REQ-0002（IDの廃止を再利用しないこと）を満たすための、廃止操作そのものをCLIから実行できること。廃止情報の台帳への追記を人間・AIが手で行う運用（実装指示書 r3 §9、`45-implementation-diff.md` に記載の未実装事項）を廃止し、`saalco retire` コマンドで機械的に行う。

1. `saalco retire <ID> [--reason TEXT] [--superseded-by ID]` により、`docs/ids.ledger` 内の該当IDの既存の行を `status: retired` にできること。変更は、その行の `status`・`reason`・`superseded_by` 列のみを対象とし、他の行・他の列を変更しないこと。
2. 台帳の書き換えは原子的（一時ファイルへの書き出し・検証後の置換）であり、行を削除しないこと。
3. 存在しないIDを指定した場合、既に `retired` のIDを指定した場合は、exit code 2 で拒否され、対象ID・原因・次に取るべき操作を示すエラーメッセージを出すこと。
4. `--superseded-by` に、台帳に存在しないID、`retired` のID、書式が不正なIDを指定した場合は、exit code 2 で拒否されること。
5. `--reason` にタブまたは改行を含む場合は、exit code 2 で拒否されること（台帳がタブ区切りであるため）。
6. `saalco retire` は実行後、廃止したIDと、「該当する項目見出しと参照を文書から削除すること（削除しなければ `saalco check` が再利用・参照残存のERRORを報告する）」という案内を出力すること。
7. `saalco retire` はドキュメントを一切変更しないこと（台帳のみを変更する）。
8. `saalco retire` は、ID採番（`saalco new`）と同じ `.saal/ids.lock` による排他制御を用いること。

### REQ-0004: Generate document and AGENTS.md templates in Japanese body text

covers: -
verify: test

規則 11.5（記述言語）を、`saalco init`／`saalco new` が生成する文書に反映すること。現状、生成される本文（`AGENTS.md` を含む）は英語のままであり、SAALCO自身のリポジトリの `AGENTS.md`（2026-09-24 に日本語で書き直し済み）と、新規プロジェクトで生成される `AGENTS.md` の内容が食い違っている。

1. `saalco new` が生成する各文書の本文（`00-meta.md` の `## Overview` 等の見出し文言を除く固定文言部分、`45-implementation-diff.md` の `## Implemented but not designed`/`## Designed but not implemented` の箇条書き既定値、`70-acceptance.md` の既定文、`80-outcome.md` の項目ラベル）が日本語で生成されること。
2. `saalco init` が生成する `AGENTS.md` の本文が、規則 11.5 の「記述言語」節を含めて日本語で生成されること。
3. 前項の変更後も、front matter のキー（`kind`・`feature`・`status`・`tier` 等）、項目見出し `### ID: Title` の `ID` と `Title`、`covers:`/`verify:`/`static:` などSAALCOが照合する固定の項目名、節見出し（`## Overview`・`## Implemented but not designed`・`## Designed but not implemented`）は英語のまま変更されないこと。
4. `80-outcome.md` の項目ラベル（`code commit`・`release version` 等）は日本語化されるが、`saalco` がこれらの行を機械的に照合する仕様（実装指示書 §18）は無いため、`checks`/`trace` の判定結果に影響しないこと。
5. `saalco check` の判定（ヘッダキー、`covers:`/`verify:`、承認hash等）が、本文言語の変更によって変化しないこと。
