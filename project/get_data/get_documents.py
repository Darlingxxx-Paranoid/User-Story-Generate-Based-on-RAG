import os
import time
import re
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm import tqdm

BASE_URL = "https://docs.4gaboards.com"
START_PATH = "/docs/user-manual"
START_URL = urljoin(BASE_URL, START_PATH)

OUTPUT_DIR = "../../user_docs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Selenium 设置
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)


def sanitize_filename(path: str) -> str:
    """将 URL path 转换为安全的文件名"""
    slug = path.strip("/").split("/")[-1] or "index"
    slug = re.sub(r"[^\w\-]+", "-", slug)
    return slug + ".md"


def fetch_and_convert_to_markdown(url: str) -> tuple[str, str]:
    """获取页面内容并转换为 markdown"""
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "lxml")

    article = soup.find("article")

    title_tag = article.find("h1")
    title = title_tag.text.strip() if title_tag else "Untitled"

    content_html = str(article)
    content_md = md(content_html)

    markdown = f"{content_md}"
    return sanitize_filename(urlparse(url).path), markdown


def extract_internal_doc_links(markdown: str) -> list:
    """从 user-manual 页面提取子文档链接"""
    links = []
    base_path = urlparse(BASE_URL).path

    matches = matches = re.findall(r"\]\((/docs/[^)]+)\)", markdown)
    for match in matches:
        full_url = urljoin(BASE_URL, match)
        links.append(full_url)

    return list(set(links))  # 去重


def main():
    print(f"正在抓取主页面：{START_URL}")
    driver.get(START_URL)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "lxml")

    # 主页面也保存
    try:
        filename, markdown = fetch_and_convert_to_markdown(START_URL)
        filename = "For Users.md"

        # 对最高层级的主页面添加说明
        markdown = "This is mainpage of For User documents\n\n" + markdown
        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(markdown)
    except Exception as e:
        print(f"❌ 主页面抓取失败：{e}")

    # 抽取子页面链接
    sub_links = extract_internal_doc_links(markdown)
    print(f"✅ 找到 {len(sub_links)} 个子链接，开始抓取...")

    for url in tqdm(sub_links):
        try:
            filename, markdown = fetch_and_convert_to_markdown(url)

            lines = markdown.splitlines()
            markdown = "\n".join(lines[3:])  # 删除前两行

            # 删除 "On this page" 及其以下内容（直到下一个标题或段落）
            markdown = re.sub(r"(?mi)^on this page\s*\n(?:[-*].*\n)*\n*", "", markdown)

            with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                f.write(markdown)
        except Exception as e:
            print(f"❌ 抓取失败: {url}，错误: {e}")

    print(f"\n🎉 所有页面已保存至 {OUTPUT_DIR}/ 文件夹。")


if __name__ == "__main__":
    main()
    driver.quit()
