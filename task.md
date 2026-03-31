# Mora — 改善タスク一覧

最終更新: 2026-04-01

**凡例**
- 担当 🤖 = AIが自動修正可能
- 担当 👤 = masaruが手動で対応が必要
- ステータス: `未着手` / `進行中` / `完了`

---

## 🔴 Phase 1 — 今すぐ必須（顧客提供前に完了させること）

---

### T01 — LINEトークンを環境変数に移す

- **担当**: 👤 masaru（手動）
- **ステータス**: 完了
- **問題**: `master_config.json` にLINEのChannel SecretとAccess Tokenが平文で書かれている。このファイルが外部に漏れると、Botを乗っ取られる。
- **対応方針**: Railway/Vercelの環境変数設定画面に移行し、ファイルからは削除する。

#### 手順（Railwayの場合）

1. [railway.app](https://railway.app) にログインし、対象のプロジェクトを開く
2. 上部メニューの **「Variables」** タブをクリック
3. **「+ New Variable」** ボタンで以下を追加する

| 変数名 | 値（master_config.jsonから転記） |
|---|---|
| `LINE_CHANNEL_SECRET_default` | defaultのline_channel_secret |
| `LINE_CHANNEL_ACCESS_TOKEN_default` | defaultのline_channel_access_token |
| `LINE_CHANNEL_SECRET_test_bot` | test_botのline_channel_secret |
| `LINE_CHANNEL_ACCESS_TOKEN_test_bot` | test_botのline_channel_access_token |

4. 設定後、`master_config.json` の各トークン値を削除（`"line_channel_secret": ""` のように空にする）
5. `.gitignore` に `master_config.json` が含まれているか確認する

> ⚠️ トークンを環境変数に移したら、コード側（clients.py）の読み込み方法もAIが修正します（T01と連動）。

---

### T02 — LINE署名検証のバイパスバグを修正

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `app.py` の署名検証関数で、`channel_secret` が空の場合に検証をスキップして `True` を返している。これにより、偽のリクエストを受け入れてしまう。
- **対応方針**: channel_secretが空の場合はリクエストを拒否するよう修正する。
- **完了条件**: channel_secretが未設定の場合に403エラーを返すことを確認。

---

### T03 — 管理画面のパスワードを強化する

- **担当**: 👤 masaru（手動）+ 🤖 AI（コード修正）
- **ステータス**: 完了
- **問題1**: パスワードがURLに `?pw=PASSWORD` の形で露出しており、ブラウザ履歴やサーバーログに残る。
- **問題2**: デフォルトパスワードが `admin123` のまま。

#### 手順（masaru担当部分）

1. Railwayの **「Variables」** タブを開く
2. `ADMIN_PASSWORD` という変数を追加し、推測されにくい長いパスワードを設定する
   - 英数字+記号を混ぜた16文字以上を推奨（パスワードマネージャーで生成するのが安全）
3. 設定後、管理画面のURLは `https://あなたのドメイン/admin` でアクセスし、Basic認証ダイアログでパスワードを入力する形式に変わります（AIがコードを修正）

---

### T04 — クライアント設定がAIに渡っていないバグを修正

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `app.py` でWebhookを処理する際、クライアントごとの設定（人格・知識ソースなど）をAI（`get_gemini_response`）に渡す引数 `client_config` が `None` のまま渡されている箇所がある。これにより、どのクライアントのユーザーが話しかけても同じデフォルト設定で動いてしまっている。
- **対応方針**: Webhookの処理フローで `client_config` を正しく取得してAIに渡すよう修正する。
- **完了条件**: client_A用のBotにメッセージを送ると、client_Aの人格・知識で返答することを確認。

---

### T05 — 並列処理でのユーザーID混在リスクを解消

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `core/agent.py` でユーザーIDをグローバル変数 `_current_user_id` で管理している。複数ユーザーが同時にメッセージを送った場合、処理が混ざってしまうリスクがある。
- **対応方針**: グローバル変数をやめ、関数の引数としてユーザーIDを受け渡すよう修正する。
- **完了条件**: 複数ユーザーが同時にメッセージを送っても、それぞれ正しいユーザーIDで処理されることを確認。

---

## 🟠 Phase 2 — 近いうちに対応（安定稼働のために）

---

### T06 — デバッグAPIを本番環境で無効化

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `/debug/vector-status` エンドポイントが認証なしで公開されており、内部状態が誰でも見られる。
- **対応方針**: 環境変数 `DEBUG_MODE=true` の場合のみ有効にするか、管理者パスワード認証を追加する。

---

### T07 — LINE APIのタイムアウトを設定

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: LINE APIへのメッセージ送信でタイムアウトが設定されていない。LINEのAPIが応答しない場合、スレッドが永久にブロックされてしまう。
- **対応方針**: `urlopen(req, timeout=10)` のように全API呼び出しにタイムアウトを設定する。

---

### T08 — ツール定義のスキーマを見直す

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `core/prompts.py` のTOOLS定義で、一部のツールのパラメータスキーマが不完全または誤っており、GeminiがツールをうまくCallできない場合がある。
- **対応方針**: 全ツール定義のスキーマを確認・修正する。

---

### T09 — リマインダー機能のclient_config渡し忘れを修正

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `core/agent.py` の `set_reminder` 関数がグローバルスコープで定義されており、クライアント設定を参照できない。
- **対応方針**: クロージャを使ってclient_configを参照できるよう修正する。

---

### T10 — Communicatorのマルチテナント対応

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: `core/communicator.py` が環境変数の固定トークンを使用しており、クライアントごとのトークンを使い分けられていない。
- **対応方針**: client_configからトークンを取得するよう修正する。

---

### T11 — 同名関数の二重定義を解消

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: プロジェクト内で同じ名前の関数が複数箇所に定義されており、どちらが呼ばれるか不明確な箇所がある。
- **対応方針**: 重複する定義を整理し、一箇所に統一する。

---

## 🔵 Phase 2.5 — Mora人格刷新（前セッションで計画・今セッションで実施）

---

### T16 — 不要ツールの削除

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: Gmail・カレンダー・ファイル作成・テンプレートなど、業務改善Q&Aボットに不要なツールをコードから削除し、回答精度を向上させる。
- **備考**: Notionのキーが一部残存している可能性あり。T12の整理時に合わせて確認する。

---

### T17 — 人格・プロンプトの書き直し

- **担当**: 🤖 AI（叩き台） → 👤 masaru（確認・フィードバック）
- **ステータス**: 完了
- **内容**: `BASE_SYSTEM_PROMPT` を「カスタマーサポートAI」から「井崎勝の分身・業務改善の専門家Mora」に全面刷新。知識源の優先順位をGoogle Drive第一に変更。Notionへの言及を完全削除。
- **完了条件**: masaruさんが「井崎さんらしい」と感じる回答トーンになること。フィードバックがあれば随時調整。

---

### T18 — 知識ドキュメントの準備

- **担当**: 👤 masaru（手動）
- **ステータス**: 未着手
- **内容**: Google Driveにフォルダを作成し、以下を入れていく。
  - よくある質問（FAQ）
  - サービス概要
  - 業務改善の考え方・事例
  - その他、Moraに参照させたいドキュメント
- **備考**: 何を書けばいいか迷ったらAIがサポートする。

---

## 🟢 Phase 3 — 余裕があるとき（将来の整備）

---

### T12 — テスト・デバッグファイルの整理

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `get_models.py`、`run_local_conversation.py` など開発中の個人用ファイル、`_legacy_backup/`・`tests/` フォルダ、テスト出力テキスト、旧Koto設定ファイル（`koto_config.json`・`utils/config.py`）、Pinecone APIキーが平文記載されていた `Pineconememo` を削除。

---

### T13 — Pineconeのテナント完全分離

- **担当**: 🤖 AI
- **ステータス**: 完了
- **問題**: 長期記憶（Pinecone）のnamespace設定が、クライアント間で混在する可能性がある。
- **対応方針**: `_scoped_user_id(client_id, user_id)` を導入し、全Pinecone操作で `"{client_id}_{user_id}"` をキーとして使用。`agent.py`・`profiler.py`・`historian.py`・`app.py` の全呼び出し箇所に `client_id` を伝搬。`search_knowledge_base` のグローバル変数依存も除去。

---

### T14 — クライアント追加手順書の作成

- **担当**: 👤 masaru + 🤖 AI
- **ステータス**: 完了
- **内容**: `client_onboarding.md` を新規作成。LINE設定・Driveフォルダ作成・スプレッドシート作成・マスターレジストリ登録・動作確認の手順とチェックリストを記載。

---

### T15 — エラーメッセージのユーザー向け改善

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `core/agent.py` の `f"エラーが発生しました: {e}"` と `core/communicator.py` の技術的エラー文言を、「ただいま混み合っております。しばらくしてから再度お試しください。」などお客様向けの自然な文言に変更。

---

## 🟣 Phase 4 — Moraを育てる（中長期の価値向上）

> Phase 1〜3完了後、Moraをより「井崎さんらしく・使いやすく」育てるための機能群。

---

### T19 — 自動エスカレーション機能

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `utils/escalation.py` を新規作成。`should_escalate()` で「井崎に直接ご確認ください」フレーズを検知し、Google Sheetsに記録 + 井崎さんのLINEに通知。管理画面 (`/admin/escalations`) で一覧確認・回答送信が可能。
- **必要な環境変数**: `ESCALATION_SHEET_ID`、`IZAKI_LINE_USER_ID`

---

### T20 — 問い合わせレポート自動生成

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `utils/inquiry_log.py` を新規作成。全回答をGoogle Sheetsに記録し、`/admin/report?period=weekly|monthly` で集計レポートを生成。`?send_line=1` で井崎さんのLINEに送信可能。
- **必要な環境変数**: `INQUIRY_LOG_SHEET_ID`

---

### T21 — 回答フィードバック機能

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `utils/feedback.py` を新規作成。100文字超の回答をGoogle Sheetsに蓄積。`/admin/feedback/digest` で未評価の回答をLINEに日次ダイジェスト送信。井崎さんが「Fxxxxxx ○」「Fxxxxxx × 修正内容」と返信することでフィードバックを記録。
- **必要な環境変数**: `FEEDBACK_SHEET_ID`

---

### T22 — Google Meet議事録自動作成・LINE送信

- **担当**: 🤖 AI
- **ステータス**: 完了
- **内容**: `utils/meeting_minutes.py` を新規作成。`MEET_TRANSCRIPT_FOLDER_ID` フォルダ内の未処理Googleドキュメントを検出 → Geminiで議事録生成 → 井崎さんのLINEに送信。`/admin/minutes/process` エンドポイントで手動実行可能。
- **実現イメージ**: Google Meetの文字起こし → フォルダに保存 → `/admin/minutes/process` 呼び出し（手動 or 定期実行） → LINE送信
- **必要な環境変数**: `MEET_TRANSCRIPT_FOLDER_ID`、`MEET_PROCESSED_SHEET_ID`（処理済み管理用）

---

## 進捗サマリー

| Phase | タスク数 | 完了 | 残り |
|---|---|---|---|
| 🔴 Phase 1 | 5 | 5 | 0 |
| 🟠 Phase 2 | 6 | 6 | 0 |
| 🟢 Phase 3 | 4 | 0 | 4 |
| 🔵 Phase 2.5 | 3 | 2 | 1 |
| 🟣 Phase 4 | 4 | 4 | 0 |
| **合計** | **22** | **21** | **1** |

---

## 既に完了した作業

| 日付 | 作業内容 |
|---|---|
| 2026-03-30 | 「Koto」→「Mora」への名前変更（全36ファイル） |
| 2026-03-30 | Notion連携の削除（agent.py・sheets_config.py・notion_ops.py） |
| 2026-03-31 | T16: 不要ツールの削除（Gmail・カレンダー・テンプレート等） |
| 2026-04-01 | T17: BASE_SYSTEM_PROMPTの全面書き直し（Mora人格・井崎さんの分身として設定） |
