# Amazon Prime Video アニメチェッカー

Amazon Prime Video で視聴中のアニメの視聴状況を一括確認するツール。

複数の作品 URL を入力するだけで、各作品の「視聴済み話数 / 総話数」と視聴ステータスをまとめて表示する。前回チェックから変化があった作品は赤字でハイライトされる。

## スクリーンショット

```
タイトル → 12/24話  視聴済み
タイトル → 11/12話  最新話配信前    ← 前回から変化あり（赤字）
タイトル → 0/13話   未視聴
```

## 仕組み

- **バックエンド**: Flask サーバーが Playwright (Chromium) を操作して Amazon Prime Video のページをスクレイピング
- **フロントエンド**: ブラウザで開く静的 HTML。結果・URL リストは `localStorage` に保存され、次回起動時に復元される
- **ページネーション対応**: 24 話を超える作品も最終ページへ自動移動して正確な話数を取得

### 判定ステータス

| ステータス | 意味 |
|---|---|
| 視聴済み | 配信中の全話を視聴済み |
| 未視聴 | 未視聴の話がある |
| 最新話配信前 | 最新話がまだ配信されていない（視聴可能な話は全話視聴済み） |

## セットアップ

### 依存ライブラリのインストール

```bash
pip install flask flask-cors playwright
playwright install chromium
```

### Amazon へのログイン（初回のみ）

Playwright でブラウザを起動してログインし、セッション情報を `state.json` に保存する。

```bash
python login.py
```

ブラウザが起動したら Amazon にログインし、完了したらターミナルで Enter を押す。

## 使い方

1. Flask サーバーを起動する

   ```bash
   python check.py
   ```

2. ブラウザで `http://127.0.0.1:5000` を開く

3. テキストエリアにチェックしたい作品の URL を 1 行ずつ入力して「実行」をクリック

## ファイル構成

```
prime_anime/
├── check.py        # Flask サーバー / Playwright スクレイピング本体
├── checker.html    # フロントエンド UI
├── login.py        # ログインセッション保存スクリプト
└── state.json      # Playwright セッション状態（login.py で生成・要 .gitignore）
```

## デプロイへの挑戦（`github-deploy` ブランチ）

ローカル専用ツールをクラウドで動かそうと試みた形跡が `github-deploy` ブランチに残っている。

- GitHub Actions ワークフロー (`.github/workflows/check.yml`) を追加し、Playwright をサーバーレスに近い環境で動かす構成を試みた
- Amazon Prime Video のボット検出により安定した動作が困難で、現在はローカル実行に戻している（参考: コミット `6009c5c` "change to deploy"、`4d6d1ee` "Measures to Detect Bots"）

## 注意事項

- `state.json` には Amazon のログインセッション情報が含まれるため、`.gitignore` に追加済み
- Amazon Prime Video の DOM 構造変更によりスクレイピングが動作しなくなる可能性がある
- 個人利用を前提としたツール
