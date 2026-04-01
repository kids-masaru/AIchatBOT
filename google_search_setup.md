# Google検索機能のセットアップガイド

Vercelなどの無料サーバーでは、DuckDuckGoなどの無料検索がブロックされることが多いため、Google公式の「Custom Search API」を使います。
（1日100回まで無料です）

## 1. 検索エンジンの作成 (Search Engine ID)

1.  **Google Programmable Search Engine** にアクセスします。
    *   URL: [https://programmablesearchengine.google.com/](https://programmablesearchengine.google.com/)
2.  「追加」または「Create」をクリックします。
3.  **検索するサイト**: 「ウェブ全体を検索」を選択（または `www.google.co.jp` などを指定）。
    *   ※「ウェブ全体」のオプションがない場合、一旦 `www.google.com` と入力し、作成後に設定変更で「ウェブ全体を検索」をONにします。
4.  **言語**: 日本語
5.  **検索エンジンの名前**: Moraなど（なんでもOK）
6.  「作成」をクリック。
7.  作成完了画面、または設定画面に表示される **「検索エンジンID (CX)」** をコピーします。
    *   例: `0123456789abcdef:ghijklmno`

## 2. APIキーの取得 (API Key)

※すでにGemini用のAPIキーをお持ちの場合、同じプロジェクトで「Custom Search API」を有効化すれば、同じキー(`GEMINI_API_KEY`)を使える場合があります。

1.  **Google Cloud Console** にアクセス。
    *   URL: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  上部の検索バーで **「Custom Search API」** を検索して選択。
3.  「有効にする (ENABLE)」をクリック。
4.  APIキーを作成していない場合は、「認証情報」から「APIキーを作成」してコピーします。

## 3. Vercelへの設定

Vercelのプロジェクト設定（Settings -> Environment Variables）に行き、以下を追加します。

*   **Key**: `GOOGLE_CSE_ID`
*   **Value**: (手順1でコピーした検索エンジンID)

※ `GOOGLE_API_KEY` という名前でAPIキーを登録しても良いですが、未登録の場合は自動的に `GEMINI_API_KEY` を使おうとします。もしGeminiと別のキーを使う場合は `GOOGLE_API_KEY` も登録してください。

## 完了

これでBotは「Google公式の検索機能」を使えるようになり、確実に検索結果の内容を読み取れるようになります。
