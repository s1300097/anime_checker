from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.amazon.co.jp/ap/signin")
    input("ログイン完了したらEnterを押してください")
    context.storage_state(path="state.json")
    browser.close()
