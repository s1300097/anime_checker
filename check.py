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

                    # --- 判定ルール ---

                    # A: 最新話の配信前判定
                    latest_ep = episode_locator.last
                    play_button = latest_ep.locator("a[data-testid='episodes-playbutton']").first
                    pre_airing = (play_button.count() == 0)

                    # B: 配信前を除いた視聴可能話数
                    avail_on_this_page = ep_count - (1 if pre_airing else 0)

                    if total_episodes is not None:
                        total_available = total_episodes - (1 if pre_airing else 0)
                    else:
                        total_available = avail_on_this_page  # DOM カウンターなしのフォールバック

                    # C: 前ページ分の話数オフセット（ページネーション対応）
                    page_offset = max(0, total_available - avail_on_this_page)

                    # D: 現ページを後ろから走査して最後に視聴済みのエピソードを探す
                    last_watched_index = -1
                    for i in range(avail_on_this_page - 1, -1, -1):
                        ep_el = episode_locator.nth(i)
                        watched_el = ep_el.locator("[data-is-watched]").first
                        if watched_el.count() > 0:
                            val = watched_el.get_attribute("data-is-watched", timeout=5000)
                            if val == "true":
                                last_watched_index = i
                                break

                    # E: 視聴済み話数を確定
                    if last_watched_index >= 0:
                        watched_count = page_offset + last_watched_index + 1
                    elif page_offset > 0:
                        # 現ページに視聴済みなし・前ページあり → 前ページは全話視聴と仮定
                        watched_count = page_offset
                    else:
                        watched_count = 0

                    # F: ステータス判定
                    if pre_airing and watched_count >= total_available:
                        status = "最新話配信前"
                    elif watched_count >= total_available:
                        status = "視聴済み"
                    else:
                        status = "未視聴"

                    results.append({
                        "url": url,
                        "title": title,
                        "watched": watched_count,
                        "total": total_available,
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
