import re
from flask import Flask, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright
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
            try:
                page = context.new_page()

                for url in urls:
                    print(f"【DEBUG】アクセス中: {url}")
                    page.goto(url, wait_until="domcontentloaded")

                    try:
                        page.wait_for_selector("h1[data-automation-id='title']", timeout=10000)
                        title = page.locator("h1[data-automation-id='title']").inner_text()
                    except Exception:
                        title = url

                    # エピソード要素が出るまで待機（最大30秒）
                    try:
                        page.wait_for_selector("div[data-testid='episode-packshot']", timeout=30000)
                    except Exception:
                        results.append(f"{title} → エピソード情報が取得できません")
                        continue

                    # ページネーション対応: 24話超の場合、最終ページへ移動
                    pagination = page.locator("div.sortDropList-Iq9XTB")
                    if pagination.count() > 0:
                        page_items = page.locator("div.sortDropList-Iq9XTB ul li a._1NNx6V")
                        last_item = page_items.last
                        last_classes = last_item.get_attribute("class") or ""
                        if "_326rd1" not in last_classes:
                            print("【DEBUG】ページネーション検出: 最終ページへ移動します")
                            page.locator("label[for='av-droplist-pagination-droplist']").click()
                            last_item.click()
                            page.wait_for_selector("div[data-testid='episode-packshot']", timeout=15000)

                    # 総エピソード数をカウンターdivから取得
                    total_ep_locator = page.locator("div.episodeCount-AH4m9k")
                    total_episodes = None
                    if total_ep_locator.count() > 0:
                        count_text = total_ep_locator.first.inner_text()  # e.g. "26 エピソード"
                        match = re.search(r'\d+', count_text)
                        if match:
                            total_episodes = int(match.group())
                            print(f"【DEBUG】総エピソード数: {total_episodes}")

                    # エピソード件数を取得
                    episode_locator = page.locator("div[data-testid='episode-packshot']")
                    ep_count = episode_locator.count()
                    if ep_count == 0:
                        results.append(f"{title} → エピソード情報が見つかりません")
                        continue

                    # 最新エピソードを取得（最後の要素）
                    latest_ep = episode_locator.last
                    # ep_number は 0-based index。返却時に +1 して実際のエピソード番号にする
                    ep_number = (total_episodes - 1) if total_episodes is not None else (ep_count - 1)

                    # 判定ルール
                    play_button = latest_ep.locator("a[data-testid='episodes-playbutton']").first
                    watched_div = latest_ep.locator("div.ymkpgm, div.packshot-hhX9n2").first

                    if play_button.count() == 0:
                        status = "配信前"
                        if ep_count >= 2:
                            prev_watched = episode_locator.nth(ep_count - 2).locator("div.Ypm4jh")
                            if prev_watched.count() > 0 and prev_watched.first.get_attribute("data-is-watched", timeout=5000) == "false":
                                status = "未視聴"
                                ep_number -= 1
                    else:
                        is_watched = watched_div.get_attribute("data-is-watched", timeout=5000)
                        if is_watched == "true":
                            status = "視聴済み"
                        else:
                            status = "未視聴"

                    results.append({
                        "url": url,
                        "title": title,
                        "ep_info": ep_number + 1,
                        "status": status
                    })

                    print(f"【DEBUG】処理完了: {title}")

            finally:
                context.close()
                browser.close()

        print("【DEBUG】最終結果:", results)
        return jsonify({"results": results})

    except Exception as e:
        print("【ERROR】例外発生:", e)
        return jsonify({"results": [f"サーバーエラー: {e}"]}), 500


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
