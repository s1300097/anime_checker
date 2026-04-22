# prime_anime

Amazon Prime Video の視聴状況を自動チェックする個人用ツールです。
GitHub Actions で定期実行し、GitHub Pages で結果を表示します。

## 機能

- 登録したアニメ作品の視聴状況を自動チェック（毎時）
- 視聴済み話数 / 総話数 を表示（例: `5/12話`）
- 最新話が配信前かつ全話視聴済みのとき「最新話配信前」と表示
- 前回チェックから変化があった作品を赤色でハイライト
- サイト上で URL リストを編集・保存（localStorage）
- PAT を設定すれば GitHub API 経由で URLs を同期し Actions に即反映

## アーキテクチャ

```
[GitHub Actions] ─── 毎時 or 手動実行
       │
       ├─ Secrets から state.json（Amazon セッション）を復元
       ├─ urls.txt を読み込み
       ├─ Playwright で Amazon Prime Video をチェック
       └─ results.json を生成 → gh-pages branch に deploy
                                       │
                              [GitHub Pages]
                                       │
                              ブラウザで閲覧 / URL 管理
```

## セットアップ

### 1. リポジトリを private で作成・push

URL リストや視聴状況を公開したくない場合は private リポジトリを推奨します。

```bash
git remote add origin https://github.com/<owner>/prime_anime.git
git push -u origin main
```

### 2. Amazon セッションを取得（初回・セッション切れ時）

```bash
pip install -r requirements.txt
playwright install chromium
python login.py
```

ブラウザが開くので Amazon にログインし、Enter を押すと `state.json` が生成されます。

### 3. `state.json` を GitHub Secrets に登録

PowerShell で Base64 エンコードしてクリップボードにコピー：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("state.json")) | Set-Clipboard
```

GitHub リポジトリ → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `AMAZON_STATE` | コピーした文字列 |

### 4. GitHub Pages を有効化

**Settings → Pages → Source** で以下を選択：

- **Public リポジトリ**: `Deploy from a branch` → Branch: `gh-pages` / `/ (root)`
- **Private リポジトリ**: `GitHub Actions`（別途 workflow の修正が必要）

### 5. 初回手動実行

**Actions タブ → Check Anime Status → Run workflow**

`results.json` が生成され、Pages に反映されます。

---

## URL リストの管理

サイト（GitHub Pages）下部の **「▼ URL・設定管理」** から編集できます。

### ローカルに保存（PAT 不要）

テキストエリアを編集 → **「ローカルに保存」**

- ブラウザの localStorage に保存
- 次回アクセス時も内容が残る
- Actions には反映されない（Actions は `urls.txt` を参照）

### GitHub に同期（Actions にも反映）

以下を設定欄に入力 → **「保存 + GitHub に同期」**

| 項目 | 内容 |
|---|---|
| GitHub PAT | `contents: write` スコープのみで OK |
| Owner | GitHub ユーザー名 |
| Repo | リポジトリ名 |

PAT・Owner・Repo はブラウザの localStorage に保存されます（GitHub には送信されません）。

---

## 判定ルール

| 状況 | 表示 |
|---|---|
| 全話視聴済み | `12/12話  視聴済み` |
| 途中まで視聴 | `5/12話  未視聴` |
| 全話視聴済み・次話配信前 | `12/12話  最新話配信前` |
| 途中視聴・次話配信前 | `5/12話  未視聴` |

- 配信前の話数は総話数・視聴済み話数の両方から除外されます
- 前回チェックから変化があった作品は赤色で表示されます

---

## ローカルでの実行

GitHub Actions を使わず手元で確認したい場合：

```bash
# 1. state.json を用意（login.py 参照）
# 2. urls.txt に URL を記載
python check.py
# → results.json が生成される

# 3. ブラウザで表示（CORS 対策のため http.server を使う）
python -m http.server 8000
# http://localhost:8000/checker.html
```

---

## ファイル構成

```
prime_anime/
├── check.py                    # メインスクリプト（Playwright でチェック・results.json 生成）
├── checker.html                # フロントエンド UI（GitHub Pages で配信）
├── login.py                    # Amazon ログイン用（state.json 生成・手元で1回だけ実行）
├── urls.txt                    # チェック対象 URL リスト
├── requirements.txt            # Python 依存パッケージ
├── .gitignore                  # state.json / results.json を除外
└── .github/
    └── workflows/
        └── check.yml           # GitHub Actions 定義（毎時実行 + 手動実行）
```

> `state.json`（Amazon セッション）と `results.json`（チェック結果）は `.gitignore` に含まれており、リポジトリには含まれません。

---

## セッション切れへの対応

Amazon のセッションクッキーは定期的に失効します。Actions が失敗し始めたら以下を実施してください。

1. ローカルで `python login.py` を再実行して `state.json` を更新
2. 再度 Base64 エンコードして GitHub Secrets の `AMAZON_STATE` を更新
