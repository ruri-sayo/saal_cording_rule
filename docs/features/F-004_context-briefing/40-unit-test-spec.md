---
kind: UT
feature: F-004
status: draft
---

# Unit Test Spec

### UT-0007: Phase inference and briefing unit test specification

covers: DD-0007, DD-0008
verify: test

一時ディレクトリに Feature の文書を置き、`saalco.context` の公開関数を呼んで次を確認する。

- 工程の推定：DD-0007 の表の1〜7の各条件について、その条件だけを満たす状態を作り、対応する工程になる。承認後に文書を変えて hash が一致しない場合は承認済みとみなさない。Tier S では AD が無くても `ad` にならない。Tier が不正なら `dd`。UT の項目に `verify: test` があっても `impl` の判定に数えない。
- 行範囲：項目見出しの行から次の見出しの直前まで、末尾の空行を除いた範囲になる。ファイルの最後の項目も正しく求まる。
- 項目の一覧：他の Feature の項目は、`covers:` で推移的に到達するものだけが `Upstream:` に並ぶ。`verify:` を省略した項目は `[test]` と表示される。
- `Read next`：工程ごとに DD-0008 の表のとおりの箇所が並ぶ。
- `Rules`：`saal_rules_version` が 1.1 のとき `3.4` を含まず、1.2 のとき含む。
- `Check`：Feature に関係する行だけが並び、20行を超えた分は `... <n> more` になる。
- 上限：項目を多数作ると、テキストが200行以内に収まり、省いた件数が示される。JSON は絞られない。
- 決定論性：同じ状態で2回組み立てた出力が一致する。

### UT-0008: approve completion output unit test specification

covers: DD-0009
verify: test

- `saalco.commands.approve` が、承認した文書ごとに相対パス・承認後の version・Feature ID を、渡された順に返す。
- 2つの Feature の文書を一度に承認すると、`Approved:` 行が渡された順に並び、`Next:` 行が Feature ID の昇順に1行ずつ出る。
- 工程の推定が例外を出すように置き換えると、`Approved:` 行だけが出て exit 0 になる。
- 承認が失敗する場合（TTY でない）は、標準出力に何も出ない。
