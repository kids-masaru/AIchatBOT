# Google Workspace機能（ドライブ・Gmail）のセットアップ

MoraがGoogleドライブやGmailにアクセスするには、権限の設定が必要です。
あなたは「Google Workspaceの管理者」ですので、**方法B（ドメイン全体の委任）** が最も便利で強力です。

---

## 【推奨】方法B：ドメイン全体の委任 (Domain-Wide Delegation)
**※Workspace管理者向け**
この設定を行うと、Botが**あなた（または指定したユーザー）になりすまして**操作できるようになります。
いちいちフォルダを共有しなくても、あなたのGmailを読んだり、マイドライブに直接ファイルを作ったりできます。

### 1. Google Cloud側での準備
1.  **Google Cloud Console** > **APIとサービス** > **ライブラリ** を開きます。
2.  以下のAPIをすべて検索して「有効」にします。
    *   Gmail API
    *   Google Drive API
    *   Google Docs API
    *   Google Sheets API
    *   Google Slides API
3.  **IAMと管理** > **サービスアカウント** を開きます。
4.  使用しているサービスアカウントをクリックします。
5.  **「一意のID (Unique ID, Client ID)」**（数字の羅列）をコピーして控えておきます。
    *   例: `109876543210987654321`

### 2. Google Workspace管理コンソールでの設定
1.  **Google Admin Console** (admin.google.com) にログインします。
2.  **セキュリティ (Security)** > **アクセスとデータ管理 (Access and data control)** > **APIの制御 (API controls)** を開きます。
3.  画面下部の **「ドメイン全体の委任 (Domain-wide delegation)」** にある **「ドメイン全体の委任を管理 (Manage Domain Wide Delegation)」** をクリックします。
4.  **「新しく追加 (Add new)」** をクリックします。
5.  **クライアントID**: 先ほど控えた「一意のID（数字の羅列）」を入力します。
6.  **OAuthスコープ**: 以下のURLを**カンマ区切り**で入力します（改行せず、カンマでつなげてください）。
    ```text
    https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/forms
    ```
7.  **「承認 (Authorize)」** をクリックします。

### 3. Vercelへの設定
Vercelの環境変数に以下を追加します。

*   **Key**: `GOOGLE_DELEGATED_USER`
*   **Value**: (Botに操作させたいユーザーのメールアドレス。あなたのメアドでOKです)

これで設定完了です！
フォルダ共有などをしなくても、Botは「あなたとして」Gmailを確認したり、ドライブに保存したりできるようになります。

---

## 方法A：フォルダ共有のみ（Gmail不可）
※上記の方法Bを行った場合は、こちらは不要です。

1.  Vercelの `GOOGLE_SERVICE_ACCOUNT_KEY` の内容から `client_email` を探してコピーします。
2.  Googleドライブで作業用フォルダを作り、「共有」からそのメールアドレスを「編集者」として招待します。
3.  そのフォルダのID（URLの末尾）を、Vercelの `GOOGLE_DRIVE_FOLDER_ID` に設定します。
