from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from flask import send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return send_from_directory(".", "checker.html")

@app.route("/check", methods=["POST"])
def check():
    try:
        urls = request.json.get("urls", [])
        print("【DEBUG】受信したURLリスト:", urls)
        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # headless=Falseでデバッグ可
            context = browser.new_context(storage_state="state.json")
            page = context.new_page()

            for url in urls:
                print(f"【DEBUG】アクセス中......")
                page.goto(url)

                try:
                    page.wait_for_selector("h1[data-automation-id='title']", timeout=10000)
                    title = page.locator("h1[data-automation-id='title']").inner_text()
                except:
                    title = url

                # エピソード要素が出るまで待機（最大30秒）
                try:
                    page.wait_for_selector("div[data-testid='episode-packshot']", timeout=30000)
                except:
                    results.append(f"{title} → エピソード情報が取得できません")
                    continue

                # エピソード一覧を取得
                episode_cards = page.locator("div[data-testid='episode-packshot']").all()
                if not episode_cards:
                    results.append(f"{url} → エピソード情報が見つかりません")
                    continue

                # 最新エピソードを取得（最後の要素）
                latest_ep = episode_cards[-1]
                for i, ep in enumerate(episode_cards):
                    if ep == latest_ep:
                        ep_number = i
                        break

                # 判定ルール
                play_button = latest_ep.locator("a[data-testid='episodes-playbutton']").first
                watched_div = latest_ep.locator("div.Ypm4jh").first

                if play_button.count() == 0:
                    status = "配信前"
                    if episode_cards[-2].locator("div.Ypm4jh").first.get_attribute("data-is-watched") == "false":
                        status = "未視聴"
                        ep_number -= 1
                else:
                    is_watched = watched_div.get_attribute("data-is-watched")
                    if is_watched == "true":
                        status = "視聴済み"
                    else:
                        status = "未視聴"

                results.append({
                    "url": url,
                    "title": title,
                    "ep_info": ep_number,
                    "status": status
                })

                print(f"【DEBUG】処理完了")

            browser.close()
        print("【DEBUG】最終結果:", results)
        return jsonify({"results": results})

    except Exception as e:
        print("【ERROR】例外発生:", e)
        return jsonify({"results": [f"サーバーエラー: {e}"]}), 500


if __name__ == "__main__":
    app.run(debug=True)

