---
kind: DD
feature: F-004
status: draft
---

# Detailed Design

### DD-0007: Phase inference

covers: AD-0003, REQ-0008, REQ-0007
verify: test

`saalco.context` に、Feature の現在の工程を推定する関数を置く。上から順に調べ、最初に当てはまった工程とする。

「文書が承認済み」とは、文書が存在し、`status: approved` で、現在の content hash が `approved_hash` と一致することをいう。「項目が無い」とは、文書が無いか、`### ID: title` の項目が1件も無いことをいう。

| 順 | 工程 | 条件 |
|---|---|---|
| 1 | `req` | `10-requirements.md` に項目が無い、または承認済みでない |
| 2 | `ad` | Tier M/L で、`20-architecture.md` に項目が無い、または承認済みでない |
| 3 | `dd` | `00-meta.md` が承認済みでない。または `30-detailed-design.md` に項目が無い、または承認済みでない。または Tier L で `35-module-design.md` が同様 |
| 4 | `test-spec` | `40-unit-test-spec.md` に項目が無い。または Tier M/L で `50-integration-test-spec.md`・`60-system-e2e-spec.md` のどちらかに項目が無い |
| 5 | `impl` | この Feature の REQ・AD・DD・MD の項目のうち `verify: test`（省略時を含む）のものに、`@pytest.mark.verifies` で指すテストが1件も無いものがある |
| 6 | `verification` | RTM（`saalco.trace.generate(write=False)`）のうち、この Feature の REQ の行に `verify_status` が `verified` でないものがある |
| 7 | `acceptance` | 上のどれにも当てはまらない |

**実装指示書 §4.3 からの変更（H3 で確認してほしい判断）：** 指示書では `impl` の条件を「`verify: test` の項目に紐付くテストが PASS していない」としている。テストが PASS したかは current な Evidence が無いと分からないため、`impl` を「紐付く仕様由来テストが無い」に、`verification` を「RTM で verified でない」に分けた。テストはあるが FAIL している状態は `verification` になる。

- Tier は `00-meta.md` の `tier:` を使う。値が S・M・L 以外なら `S` として扱わず、工程を `dd` とする（Tier の決定は H3 の工程であるため）。
- UT・IT・ST・DEV の項目は、5 の対象にしない（これらはテストから指される側ではないため）。

### DD-0008: Briefing content, ordering, and size limit

covers: AD-0003, REQ-0008
verify: test

**テキスト出力**（ツールの出力なので英語。規則 11.5）。節の順は固定する。

```text
# Briefing F-004 context-briefing
Tier: M (approved)
Phase: dd (inferred)
Rules version: 1.1

## Documents
- 00-meta.md: approved
- 10-requirements.md: approved
- 20-architecture.md: draft
...

## Items
- REQ-0007 [test] approve prints a next-step hint for a new session — docs/features/F-004_context-briefing/10-requirements.md:9-21
...
Upstream:
- REQ-0006 [test] ... — docs/features/F-003_.../10-requirements.md:11-26

## Read next
- docs/features/F-004_context-briefing/10-requirements.md:9-21
...

## Rules
4.3, 4.4, 6.4

## Check
saalco check (static): 0 errors, 0 warnings
```

- `Tier:` の括弧内は `approved` / `not approved`。`Phase:` は、`--phase` が無ければ `(inferred)`、あれば `(given; inferred: <phase>)` とする。`Rules version:` は `docs/project.md` の `saal_rules_version` の値とする。
- `## Documents`：`TIER_FILES[tier]` の文書を、ファイル名の昇順で並べる。状態は `missing`・`draft`・`approved`・`approved (hash mismatch)`、または `status` の値そのもの（`superseded` など）とする。Tier が不正なときは `TIER_FILES["L"]` を使う。
- `## Items`：この Feature の項目（全ての種類）を ID の昇順で並べる。続けて `Upstream:` の下に、この Feature の項目の `covers:` から上流へ推移的に辿って到達する、他の Feature の項目を ID の昇順で並べる。`verify:` を省略した項目は `[test]` と表示する。行範囲は、項目見出しの行から、次の見出し（`#`〜`###`）の直前までのうち、末尾の空行を除いた範囲とする（行番号はファイル先頭からの1始まり）。
- `## Read next`：工程ごとに、次の項目の行範囲を `## Items` と同じ順で並べる。

| 工程 | 読む箇所 |
|---|---|
| `req` | `docs/input/`（ディレクトリ名だけを示す） |
| `ad` | この Feature と上流の REQ の項目 |
| `dd` | この Feature と上流の REQ・AD の項目 |
| `test-spec` | この Feature の REQ・AD・DD・MD の項目 |
| `impl` | この Feature の DD・MD・UT・IT・ST の項目と、`45-implementation-diff.md` |
| `verification` | `45-implementation-diff.md` |
| `acceptance` | `70-acceptance.md` |

- `## Rules`：実装指示書 §4.3 の表の節番号をカンマ区切りで示す。`3.4` は `saal_rules_version` が 1.2 以上のときだけ含める。
- `## Check`：`saalco.checks.run(root)`（静的）の ERROR・WARNING の件数を示す。続けて、この Feature の ID・Feature のディレクトリのパス・この Feature の項目 ID のいずれかを含む行だけを、`ERROR`・`WARNING` の順、各々文字列の昇順で、最大20行示す。超えた分は `... <n> more` とする。
- 決定論性：集合の反復順に依存しないよう、全ての一覧を上の規則で並べ替えてから出力する。日時・実行環境の情報は出さない。

**200行の上限**：組み立てたテキストが200行を超えたら、`Upstream:` を、この Feature の項目の `covers:` が直接指す項目だけに絞り、`... <n> more upstream items` を加える。それでも超えたら、`## Items` の末尾から項目を省き、`... <n> more items` を加えて200行以内にする。`## Read next` も同様に末尾から省く。

**JSON 出力**（`--json`）：キーは `feature`、`name`、`tier`、`tier_approved`、`phase`、`phase_source`（`inferred` / `given`）、`inferred_phase`、`rules_version`、`documents`（`file`・`state` の配列）、`items`（`id`・`kind`・`title`・`verify`・`path`・`start`・`end`・`upstream` の配列）、`read_next`（`path` と、項目なら `start`・`end`）、`rules`、`check`（`errors`・`warnings` の件数と `lines`）とする。行数で絞らず、`check.lines` も20行で切らない。

**エラー**：`docs/features/` に指定した Feature のディレクトリ（`F-nnn_*`）が無ければ、`ERROR <F-nnn>: feature not found.` を出して exit 2 とする。

### DD-0009: approve completion output

covers: AD-0003, REQ-0007
verify: test

- `saalco.commands.approve` は、承認した文書ごとに `(相対パス, 承認後の version, Feature ID)` を、引数で渡された順に返す。Feature ID は文書ヘッダの `feature:` とする。ヘッダの書き込みの内容と順序は変えない。
- `saalco.cli` は、`approve` が例外なく戻った後に、返された順に `Approved: <path> (version <n>)` を標準出力に出す。続けて、返された Feature ID の重複を除いて昇順に並べ、それぞれについて `saalco.context` の工程の推定を呼び、`` Next: start a new session and run `saalco context <F-nnn> --phase <phase>` `` を出す。
- 工程の推定が例外を出した場合は、`Next:` 行を出さずに exit 0 とする（承認自体は記録済みであり、表示のために承認を失敗扱いにしない）。

**実装指示書 §4.1 からの変更（H3 で確認してほしい判断）：** 指示書では `<phase>` を「承認した文書の次の工程」としている。この設計では、承認を記録した後の状態から DD-0007 で推定した工程を使う。例えば REQ を承認したときに AD がまだ未承認なら `ad` になり、文書の種類から機械的に決めるより、実際に次にすべき工程と一致するためである。
