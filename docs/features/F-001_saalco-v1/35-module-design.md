---
kind: MD
feature: F-001
status: draft
---

# Module Design

### MD-0001: SAALCO Python package modules

covers: DD-0001
verify: test

### MD-0002: Ledger parsing and retirement validation in ids and checks modules

covers: DD-0002
verify: test

`saalco.ids` が台帳の行を構造化して読む（行番号、状態、理由、置き換え先を保持する）。採番時には、タイトル中のタブを空白に置き換える。`saalco.checks` が DD-0002 の検査を行う。DEV の `rule:` にはカンマ区切りで複数の規則番号を書けるようにし、各番号と完全一致で照合する。
