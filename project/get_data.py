import os
import re
import json
from urllib.parse import urljoin, urlparse
from openai import OpenAI
from enum import Enum

BASE_URL = "https://docs.4gaboards.com"
DOCS_PATH = "../user_docs"
OUTPUT_PATH = "../data"

client = OpenAI(
    base_url="https://api2.aigcbest.top/v1",
    api_key="sk-zjyyqhELqpJQKMDy7c02C9Fy1iYHyc4CESe8mN6D8khuMYhO",
)

prompt = """
The following picture is the shot of web app 4ga Board, you are a web app tester, and you have to describe the scenario of it.
Your description contains two part:
1. The whole description of this page.(Focusing on the page, not the details)
2. The all elements in this page. In this part, you need to identify element's class(such like Button, checkbox...) and task function(as possible as simple).

Your output format must be 
{
    "scenarios of shot": "..."
    "elements in the page":[
        {
            "index": 1,
            "class": "...",
            "function":"..."
        },
    ]
}
"""


# 定义节点类型枚举
class NodeType(Enum):
    FOR_USER_DOC = "For_User_Doc"
    MODULE = "Module"
    SECTION = "Section"
    WEBSHOT = "Webshot"


# 定义边类型枚举
class EdgeType(Enum):
    HAS_MODULE = "HAS_MODULE"
    HAS_SECTION = "HAS_SECTION"
    HAS_WEBSHOT_EXAMPLE = "HAS_WEBSHOT_EXAMPLE"
    IS_WEBSHOT_EXAMPLE_OF = "IS_WEBSHOT_EXAMPLE_OF"
    CALL = "CALL"


graph = {"nodes": [], "edges": []}
node_set = set()


def extract_title(text):
    lines = text.splitlines()
    if len(lines) >= 2:
        title_line = lines[0].strip()
        underline_line = lines[1].strip()
        # 检查第二行是否全是 = 符号
        if re.fullmatch(r"=+", underline_line):
            return title_line
    return None


def extract_section(text):
    sections = []
    lines = text.splitlines()

    for i in range(1, len(lines)):
        prev_line = lines[i - 1].strip()
        current_line = lines[i].strip()
        if re.fullmatch(r"[-]{3,}", current_line):
            if prev_line:  # 确保上一行不是空行
                sections.append(prev_line)
    return sections


def extract_section_with_content(text):
    sections = []
    lines = text.splitlines()
    current_section = None
    content_start = None

    for i in range(1, len(lines)):
        prev_line = lines[i - 1].strip()
        current_line = lines[i].strip()

        # 检测section标题
        if re.fullmatch(r"[-]{3,}", current_line):
            if prev_line:  # 确保上一行不是空行
                # 如果已经有一个section在收集，先保存它
                if current_section is not None and content_start is not None:
                    # 收集从content_start到当前行之前的所有内容
                    section_content = "\n".join(lines[content_start : i - 1])
                    sections.append((current_section, section_content))

                # 开始新的section
                current_section = prev_line
                content_start = i + 1  # section标题下划线下一行开始是内容

    # 添加最后一个section
    if (
        current_section is not None
        and content_start is not None
        and content_start < len(lines)
    ):
        section_content = "\n".join(lines[content_start:])
        sections.append((current_section, section_content))

    return sections


def extract_introduce(text):
    pattern = re.compile(
        r"^=+$\n"  # ===== 标记行
        r"(.+?)"  # 要捕获的内容（非贪婪）
        r"(?=\n-+$|\Z)",  # 前瞻：-----标记行或文件结束
        flags=re.MULTILINE | re.DOTALL,
    )

    match = pattern.search(text)
    if match:
        content = match.group(1).strip()
        # 分割成行并删除最后一行
        lines = content.split("\n")
        if len(lines) > 1:
            content = "\n".join(lines[:-1]).strip()
        # 清理多余空行（保留图片和格式）
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content
    return None


def generate_scenario_description(url):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                        },
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    return response.choices[0].message.content


def replace_image_by_scenario(section, text):
    pattern = r"!\[(.*?)\]\((.*?)\)"
    index = 0

    for match in re.finditer(pattern, text):
        index += 1
        title = match.group(1)
        url = match.group(2)
        text = text.replace(
            match.group(0), f"![{title}] ({section}_shot_example_{index})", 1
        )

        # 添加节点和边（保持不变）
        caption = generate_scenario_description(urljoin(BASE_URL, url))

        add_node(
            f"{section}_shot_example_{index}",
            NodeType.WEBSHOT,
            f"The contents in {section}_shot_example_{index}\n{caption}",
        )
        add_edge(
            f"{section}",
            f"{section}_shot_example_{index}",
            EdgeType.HAS_WEBSHOT_EXAMPLE,
        )
        add_edge(
            f"{section}_shot_example_{index}",
            f"{section}",
            EdgeType.IS_WEBSHOT_EXAMPLE_OF,
        )

    return text


def extract_internal_links(section, text):
    # 只匹配 /docs/xxx 样式的内部链接
    pattern = r"\[([^\]]+)\]\(/docs/([^\)]+)\)"

    for match in re.finditer(pattern, text):
        link_text = match.group(1)
        target_module = match.group(2)

        # 构造替换链接
        new_link = f"[{link_text}](module_{target_module})"

        # 替换文本中对应链接
        text = text.replace(match.group(0), new_link, 1)

        # 添加图谱边
        add_edge(section, target_module, EdgeType.CALL)

    return text


def remove_heading_anchors(md_text):
    # 处理形如 [标题文本](#锚点 "title") 的格式，包括 title 可选项，替换成纯文本标题
    pattern = r"\[([^\]]+?)\]\(#[^\)]+\)"
    new_text = re.sub(pattern, r"\1", md_text)
    return new_text


def add_node(node_id, node_type, content=None):
    if node_id in node_set:
        return
    graph["nodes"].append({"id": node_id, "type": node_type, "content": content or {}})
    node_set.add(node_id)


def add_edge(src, tgt, rel):
    graph["edges"].append({"source": src, "target": tgt, "type": rel})


def GraphG_mainpage(text):
    title = extract_title(text)
    add_node(f"{title}", NodeType.FOR_USER_DOC, f"{title}")

    sections = extract_section(md_text)
    for section in sections:
        add_node(f"{section}", NodeType.MODULE, f"{section}")
        add_edge(f"{title}", f"{section}", EdgeType.HAS_MODULE)


def GraphG_module(text):
    title = extract_title(text)
    add_node(f"{title}", NodeType.MODULE, f"{title}")

    # 提取该module的introduce
    introduce = extract_introduce(text)
    introduce = replace_image_by_scenario(f"{title}_introduce", introduce)
    introduce = extract_internal_links(f"{title}_introduce", introduce)
    add_node(f"{title}_introduce", NodeType.SECTION, f"{title}_introduce\n{introduce}")
    add_edge(f"{title}", f"{title}_introduce", EdgeType.HAS_SECTION)

    sections = extract_section_with_content(text)
    for section in sections:
        section_content = replace_image_by_scenario(f"{title}_{section[0]}", section[1])
        section_content = extract_internal_links(
            f"{title}_{section[0]}", section_content
        )
        add_node(
            f"{title}_{section[0]}",
            NodeType.SECTION,
            f"{section[0]}\n---------------\n{section_content}",
        )
        add_edge(f"{title}", f"{title}_{section[0]}", EdgeType.HAS_MODULE)


# 主处理流程
for root, dirs, files in os.walk(DOCS_PATH):
    for file in files:
        file_path = os.path.join(root, file)
        with open(file_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        # 清洗锚点标题链接为纯文本
        text = remove_heading_anchors(md_text)

        if file == "For Users.md":
            # 最高层次
            GraphG_mainpage(text)
        else:
            GraphG_module(text)
