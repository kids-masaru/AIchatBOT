# Mora - 無料ホスティング（Vercel）デプロイガイド

LINE Bot「Mora」を完全無料で運用するための、Vercelへのデプロイ手順です。

## 1. 準備するもの
*   **GitHubアカウント**: 現在のコードがアップロードされているアカウント
*   **Vercelアカウント**: [https://vercel.com/](https://vercel.com/) からGitHubアカウントで登録（Hobbyプランは無料）

## 2. デプロイ手順

1.  **Vercelにログイン**:
    Vercelのダッシュボードに行き、「Add New...」->「Project」をクリックします。

2.  **GitHubリポジトリをインポート**:
    `mottora/mora` (または現在のリポジトリ名) を探し、「Import」ボタンを押します。

3.  **設定の確認**:
    *   **Framework Preset**: `Other` を選択します。
    *   **Build Command**: 空欄でOK
    *   **Install Command**: `pip install -r requirements.txt` (自動入力されない場合)
    *   **Output Directory**: `.` (ドット) または空欄

4.  **環境変数の設定 (Environment Variables)**:
    「Environment Variables」のセクションを開き、以下の変数を登録します（`.env` ファイルの中身と同じです）。
    
    *   `LINE_CHANNEL_SECRET`
    *   `LINE_CHANNEL_ACCESS_TOKEN`
    *   `GEMINI_API_KEY`
    *   `GOOGLE_SERVICE_ACCOUNT_KEY`
    *   `GOOGLE_DRIVE_FOLDER_ID`

5.  **デプロイ実行**:
    「Deploy」ボタンを押します。1分ほどで完了します。

## 3. LINE Developersの設定変更（重要）

デプロイが完了すると、Vercelから `https://mora-xxx.vercel.app` のようなURLが発行されます。

1.  LINE Developersコンソール ([https://developers.line.biz/](https://developers.line.biz/)) にログインします。
2.  このBotの設定画面を開きます。
3.  **Webhook URL** を、VercelのURLに変更します。
    *   変更前: `https://mora-xxx.railway.app/webhook`
    *   変更後: `https://あなたのVercelのURL/webhook`
    *   ※末尾に `/webhook` をつけるのを忘れないでください！
4.  「検証 (Verify)」ボタンを押して、「成功」と出れば完了です。

これで、維持費0円でBotを運用できます！
