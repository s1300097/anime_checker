import re
import json
import base64
import os
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright


def restore_state():
    state_b64 = os.environ.get("AMAZON_STATE", "")
    if state_b64:
        with open("state.json", "w") as f:
            f.write(base64.b64decode(state_b64).decode())


def load_urls():
    with open("urls.txt", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def check_one(page, url):
    print(f"アクセス中: {url}")
    page.goto(url, wait_until="domcontentloaded")

    try:
        page.wait_for_selector("h1[data-automation-id='title']", timeout=10000)
        title = page.locator("h1[data-automation-id='title']").inner_text()
    except Exception:
        title = url

    try:
        page.wait_for_selector("div[data-testid='episode-packshot']", timeout=30000)
    except Exception:
        return {"url": url, "title": title, "error": "エピソード情報が取得できません"}

    # ページネーション対応: 24話超の場合、最終ページへ移動
    pagination = page.locator("div.sortDropList-Iq9XTB")
    if pagination.count() > 0:
        page_items = page.locator("div.sortDropList-Iq9XTB ul li a._1NNx6V")
        last_item = page_items.last
        last_classes = last_item.get_attribute("class") or ""
        if "_326rd1" not in last_classes:
            print("ページネーション検出: 最終ページへ移動")
            page.locator("label[for='av-droplist-pagination-droplist']").click()
            last_item.click()
            page.wait_for_selector("div[data-testid='episode-packshot']", timeout=15000)

    # 総エピソード数をカウンターdivから取得
    total_ep_locator = page.locator("div.episodeCount-AH4m9k")
    total_episodes = None
    if total_ep_locator.count() > 0:
        count_text = total_ep_locator.first.inner_text()
        match = re.search(r'\d+', count_text)
        if match:
            total_episodes = int(match.group())

    episode_locator = page.locator("div[data-testid='episode-packshot']")
    ep_count = episode_locator.count()
    if ep_count == 0:
        return {"url": url, "title": title, "error": "エピソード情報が見つかりません"}

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
        total_available = avail_on_this_page

    # C: 前ページ分の話数オフセット（ページネーション対応）
    page_offset = max(0, total_available - avail_on_this_page)

    # D: 現ページを後ろから走査して最後に視聴済みのエピソードを探す
    try:
        page.wait_for_selector("[data-is-watched]", timeout=10000)
    except Exception:
        pass  # 未視聴または未ログイン状態

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

    return {
        "url": url,
        "title": title,
        "watched": watched_count,
        "total": total_available,
        "status": status,
    }


def main():
    restore_state()
    urls = load_urls()
    print(f"チェック対象: {len(urls)}件")

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="state.json")
        try:
            page = context.new_page()
            for url in urls:
                result = check_one(page, url)
                results.append(result)
                print(f"完了: {result.get('title', url)}")
        finally:
            context.close()
            browser.close()

    jst = timezone(timedelta(hours=9))
    updated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")

    output = {"results": results, "updated_at": updated_at}
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n結果: {len(results)}件 → results.json（{updated_at}）")


if __name__ == "__main__":
    main()
