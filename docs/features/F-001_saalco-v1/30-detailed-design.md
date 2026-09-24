---
kind: DD
feature: F-001
status: draft
---

# Detailed Design

### DD-0001: Implement deterministic document and verification services

covers: AD-0001
verify: test

**文書ヘッダとcontent hash（実装指示書 §8.1、§11）**

- ヘッダは `---` で囲んだフラットな `key: value` の並びとする。ネスト・リスト・クォートは解釈しない。
- 未知のキーは保持し、書き戻すときにキーの順序と無関係な本文を変更しない。
- 必須キーは `kind`・`feature`・`status`（`draft`/`approved`/`superseded`）。`00-meta.md` は追加で `tier`（S/M/L）を必須とする。
- `saalco approve` の hash 計算は SHA-256 を用い、`status`・`version`・`approved_by`・`approved_at`・`approved_hash` の5キーを除いたヘッダと本文（改行はLFに正規化）を対象とする。同じ内容からは常に同じ hash になること。
- 既存文書を書き換えるときは、一時ファイルに書き出し、再パースで検証してから原子的に置換する（実装指示書 §11、§18）。

**項目とcovers規則（実装指示書 §8.2、§8.3）**

- 見出し直下のメタ情報行は `covers:` と `verify:`。`verify:` は `test`/`review`/`static` のいずれかで、省略時は `test` とみなす。REQ項目は `covers: -` とする。
- `verify: static` の項目には `static: <gate名>` を必須とし、そのゲートが `docs/project.md` に存在し current Evidence でPASSしていれば充足とする。
- `covers:` に書ける参照先は種別ごとに固定されている（REQ: `-`／AD: REQ／DD: AD, REQ／MD: DD, AD, REQ／UT: DD, MD／IT: AD／ST: REQ／DEV: `covers:` を使わず `scope:` を使う）。この表に無い参照先、存在しないID参照、重複ID、循環参照、`covers:` が空、のいずれもERRORとする。下流から一度も参照されていないREQ・AD・DD・MDはWARNINGとする。

**テストマーカー（実装指示書 §8.4）**

- マーカーはASTで解析し、実行・importを行わない。関数デコレータ、クラスデコレータ、モジュールの `pytestmark` に対応する。
- マーカーの無いテストは `impl_aware` として扱う（既存テストの移行を含む）。
- parametrize されたテストは、全ケースPASSで1件のPASSとする。
- `verifies` の参照先種別は、`tests/unit` → DD/MD、`tests/integration` → AD、`tests/e2e` → REQ。ディレクトリと参照先種別が一致しない場合はWARNINGとする。

**current Evidence（暫定解釈 I-1）**

- Evidenceは対象commitの後続commitに記録されるため、HEADと同一commitにはなり得ない。対象commitからHEADまでの差分が `evidence/`・`docs/trace/`・`docs/ids.ledger` のみであれば、そのEvidenceをHEADに対して current とみなす。current でないEvidenceは `stale` として扱う。

**Coverage 基準（実装指示書 §15、`docs/development-open-questions.md`）**

- 基準点は、HEADの祖先にある直前EvidenceのうちCoverage結果が `PASS` のもので最も近いものとする。FAILや `NOT_EVALUATED` のEvidenceは基準点にしない（`evidence` の再実行だけではCoverageのFAILがPASSに変わらない）。Evidenceが1つも無ければ空ツリーを基準にする（初回は全コードが新規扱い）。
- 判定基準は、差分の行カバレッジが80%以上であること、かつ全体のカバレッジが基準点の値を下回らないことの両方。
- 差分カバレッジは `git diff -U0` の追加・変更行と、coverage JSONの実行行・未実行行を突き合わせて自前で計算する。coverage.pyが実行対象とみなさない行（コメント・空行）は差分カバレッジ100%として扱い、行の削除のみの変更は「変更行」に数えない。
- 計算できない場合は `NOT_EVALUATED` とし、該当するDEVが無ければFAILとして扱う（PASSにしない）。

**RTM の verified 条件（実装指示書 §14）**

- REQ行の `verify_status` が `verified` になるのは次を全て満たす場合のみ：REQ自身の検証が充足（`verifies`のSTがPASS、current な手動STがPASS、または `review`/`static` の条件充足）していること、そのREQを直接・間接に `covers:` する全ての設計項目が `verify:` の種類に応じて充足していること、`review` の充足条件が承認済みかつhash一致であること、根拠となるEvidenceが全てcurrentであること。満たさない場合は `unverified`。根拠となるEvidenceがcurrentでない場合は `stale`。判定できない場合は `NOT_EVALUATED`。

**DEV照合（実装指示書 §8.6、`docs/development-open-questions.md`）**

- Coverage未達等の例外は、`status: open` かつ `rule` と `scope` が該当するDEVがあれば、ERRORではなくWARNINGとして表示する。
- 照合は規則番号とscopeトークンの完全一致で行う。scopeトークンはFeature ID・項目ID・パスの前方一致のいずれか。`rule:` にはカンマ区切りで複数の規則番号を書ける。照合対象の規則番号は、6.4（`verifies`テスト未PASS）、6.8（RTM未verified）、7.1（ゲートのFAIL/ERROR）、7.3（Coverage）、4.6（未承認の設計に対応する実装）。
- DEVの採番も `saalco new dev` で行う。

### DD-0002: Ledger row status and retired-ID checks

covers: REQ-0002
verify: test

台帳の各行に任意の列 `status`（`active` / `retired`）、`reason`、`superseded_by` を追加する。列が無い既存の行は `active` とみなす。`saalco check` は次をERRORにする。

- `status` の値が不正であること
- `retired` のIDが台帳に複数行あること、文書の項目見出しや Feature ディレクトリとしてまだ宣言されていること（番号の再利用）
- `covers:`、`verifies` マーカー（参照先と `spec=`）、DEV の `scope:`、`docs/trace/rtm.csv` に、廃止したIDへの参照が残っていること
- `superseded_by` が、存在しないIDまたは廃止されたIDを指していること

`retired` のIDは、台帳と文書の不一致検査から除外する。採番は廃止したIDの行も含めた最大値＋1とする。

### DD-0003: Retire command validation and atomic ledger row rewrite

covers: REQ-0003
verify: test

**入力検証**

- 対象IDが台帳に存在しない場合、既に `status: retired` の場合は、いずれもexit code 2 のERRORとし、対象ID・原因（未知／廃止済み）・次に取るべき操作（IDを確認する、別のIDを指定する等）を1〜2行で示す（実装指示書 §5 のエラーメッセージ書式）。
- `--superseded-by` に指定したIDが台帳に無い場合、そのIDが `retired` の場合、ID書式（`F-nnn`/`REQ-nnnn` 等）に一致しない場合は、いずれもexit code 2 のERRORとする（実装指示書 §9「`superseded_by` を書く場合は、台帳に存在し、かつ廃止されていないIDでなければならない」）。
- `--reason` にタブまたは改行が含まれる場合はexit code 2 のERRORとする（台帳がタブ区切り1行1IDのため。実装指示書 §9「`title` にタブを含めない」と同じ制約を `reason` にも適用する）。

**原子的な行書き換え**

- 台帳ファイル全体を読み込み、対象IDの行だけを、既存の列（`ID`・`feature`・`allocated_at`・`title`）はそのまま保持し、`status`・`reason`・`superseded_by` の3列を追記・上書きする形で再構成する。他の行は一切変更しない。
- 書き換えは一時ファイルへの書き出し → 再読み込みによる検証 → 原子的な置換（`os.replace` 等）の手順で行う（実装指示書 §18「既存文書を書き換えるときは、一時ファイルに書き出し、検証してから原子的に置換する」と同じ方針を台帳にも適用する）。
- 行の削除は行わない（実装指示書 §9「行は削除しない」）。文書（`docs/features/**/*.md`）は一切変更しない。項目見出しと参照の削除は人間・Coding Agentの作業とし、コマンド完了後の案内メッセージで促す。

**排他制御**

- `saalco new` と同じ `.saal/ids.lock`（`O_EXCL`で作成）を用いて、採番と廃止が同時に走らないようにする。

**廃止後の検査への影響**

- `retired` になったIDは、`saalco check` の台帳と文書の不一致検査から除外される（DD-0002）。項目見出しや参照が文書に残っている場合は、DD-0002が定義する「廃止した番号の再利用」または「廃止したIDへの参照」としてERRORになる。`saalco retire` 自体はこれらの文書側チェックを行わない（`checks` モジュールの責務。DD-0002を参照）。

### DD-0004: Japanese-body template generation with fixed English machine-matched labels

covers: REQ-0004
verify: test

規則 11.5 の対象区分（コード／文書本文／見出し・キー・ID・固定項目名）に従い、`templates` モジュールが生成する文字列のうち、次を日本語に変更する。

**変更する生成テキスト**

- `feature_document` が返す本文中の固定文言：`45-implementation-diff.md` の既定の箇条書き（`- None` に相当する「なし」等）、`70-acceptance.md` の既定説明文（現行英語「Human-only validation record. SAALCO does not decide acceptance.」相当の日本語文）、`80-outcome.md` の項目ラベル（`code commit`・`dataset version`・`model`・`config`・`seed`・`environment`・`result location`・`result hash`／`release version`・`target commit`・`deployment target`・`release date`。日本語ラベルは `docs/glossary.md` に対応語が無いため、本DDに続けて用語を追加してから使う）。
- `AGENTS` 定数（`saalco init` が書き出す `AGENTS.md` 本文）：現行リポジトリの `AGENTS.md`（2026-09-24 にエージェントが日本語で書き直したもの。内容は本 DD の承認で確認する）と同内容・同じ11項目＋「## Language」節（規則11.5の対象・言語対応表・glossary参照・既存文書の翻訳方針・サブエージェントへの引き継ぎ方針）を、生成コードの側にも反映する。

**変更しない部分**

- front matter のキー（`kind`・`feature`・`status`・`tier` 等）と値（`draft`／`active` などの固定語彙）。
- 項目見出しの生成規則（`### {heading}` の元になる `name.removesuffix(".md").split("-", 1)[-1].replace("-", " ").title()`）と `FILE_FOR_KIND`・`KIND_FOR_FILE`・`TIER_FILES` の識別子。
- `covers:`/`verify:` 行の雛形（`saalco new <kind>` が項目に追記する雛形はキーのみで本文を持たないため、翻訳対象が無い）。
- `## Overview`・`## Implemented but not designed`・`## Designed but not implemented` の節見出し自体（機械照合対象。実装指示書 §8.2 相当の固定英語見出しとして扱う）。
- `project_document` が生成する `docs/project.md` のキー・ゲート名（`gate.NN.*`・`test.*`）。

**用語**

- 新しく使う日本語ラベル（Outcomeの項目名等）は、実装前に `docs/glossary.md` の対応表へ追加する（規則11.5「新しい用語を導入するときは、先に対応表へ追加する」）。
