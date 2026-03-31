# 新規クライアント追加手順書

最終更新: 2026-04-01

このドキュメントは、新しいクライアント企業にMoraを提供する際の設定手順をまとめたものです。

---

## 必要な情報（事前にクライアントから入手）

| 項目 | 説明 | 例 |
|---|---|---|
| クライアントID | システム内の識別子（英小文字・数字・アンダースコアのみ） | `yamada_dental` |
| ボット名 | LINEでの表示名 | `山田歯科 Mora` |
| 人格設定 | どんなキャラクターで回答させるか（1〜2行） | `丁寧で親しみやすい歯科クリニックのスタッフ` |

---

## 手順 1 — LINE公式アカウントの作成（クライアント担当）

クライアント自身に以下を実施してもらいます。

1. [LINE Developers](https://developers.line.biz/) にアクセスしてプロバイダーを作成
2. 「Messaging API」チャネルを新規作成
3. 以下の2つをメモしておく
   - **Channel Secret**（チャネル基本設定 > チャネルシークレット）
   - **Channel Access Token**（Messaging API設定 > チャネルアクセストークン）
4. Webhook URLを以下に設定する
   ```
   https://【Railwayのドメイン】/callback/【クライアントID】
   ```
   例: `https://mora.railway.app/callback/yamada_dental`

---

## 手順 2 — Google Driveフォルダの作成（masaru担当）

1. Google Driveで新しいフォルダを作成（例: `山田歯科_知識ソース`）
2. フォルダの共有設定で「リンクを知っている全員が閲覧可」または「サービスアカウントを共有」にする
3. フォルダIDをURLからコピーしておく
   ```
   https://drive.google.com/drive/folders/【フォルダID】
   ```
4. フォルダ内に以下を入れていく（T18参照）
   - よくある質問（FAQ.docx または FAQ.pdf）
   - サービス概要
   - 業務改善の事例・考え方（井崎さんが共有したいもの）

---

## 手順 3 — Googleスプレッドシートの作成（masaru担当）

各クライアント専用のスプレッドシートを作成します。

1. 新しいGoogleスプレッドシートを作成（例: `山田歯科_Mora設定`）
2. スプレッドシートIDをURLからコピー
   ```
   https://docs.google.com/spreadsheets/d/【スプレッドシートID】/edit
   ```
3. サービスアカウント（`mora-bot@...`）に「編集者」権限を付与する

---

## 手順 4 — マスターレジストリへの登録（masaru担当）

RailwayのMasterRegistryスプレッドシートに1行追加します。

| A列 | B列 | C列 | D列 | E列 | F列 | G列 |
|---|---|---|---|---|---|---|
| client_id | line_channel_secret | line_channel_access_token | spreadsheet_id | knowledge_folder_id | bot_name | personality |
| `yamada_dental` | （LINE Channel Secret） | （LINE Access Token） | （スプレッドシートID） | （DriveフォルダID） | `山田歯科 Mora` | `丁寧で親しみやすい歯科クリニックのスタッフ` |

---

## 手順 5 — Railway環境変数の追加（masaru担当）

> ⚠️ LINEトークンはスプレッドシートに書いているため、原則この手順は不要。ただし `default` クライアントの場合のみ環境変数で管理。

新クライアント追加後、Railwayの設定変更は不要です（マスターレジストリが自動で読み込まれます）。

---

## 手順 6 — 動作確認

1. LINEアプリでクライアントの公式アカウントに「テスト」とメッセージを送る
2. Moraから返答が来ることを確認
3. Google Drive内のドキュメントを参照した回答が返ることを確認

---

## チェックリスト

```
□ LINE Channel Secret・Access Token を取得済み
□ Webhook URL を設定済み（/callback/【client_id】）
□ Google Drive 知識ソースフォルダを作成済み
□ Googleスプレッドシートを作成してサービスアカウントに共有済み
□ マスターレジストリに1行追加済み
□ 動作確認済み（LINEでメッセージ送受信）
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| LINEに返答が来ない | Webhook URLが間違っている | `/callback/【client_id】` の形式を確認 |
| 「設定が見つかりません」エラー | client_idがレジストリに未登録 | マスターレジストリのA列を確認 |
| Drive内のドキュメントを参照しない | フォルダIDが間違っている | DriveフォルダのURLからIDを再確認 |

---

*このドキュメントは随時更新すること。手順が変わったらAIに「client_onboarding.mdを更新して」と伝えてください。*
