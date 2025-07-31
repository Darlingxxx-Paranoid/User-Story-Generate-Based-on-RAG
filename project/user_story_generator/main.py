import sys
import os
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent))
from chains import story_chain

if __name__ == "__main__":
    user_story_list = story_chain.generate_user_stories()
    output_dir = Path(__file__).parent.parent.parent / "user_story"
    output_dir.mkdir(parents=True, exist_ok=True)

    for user_story in user_story_list:
        # 解析内容为JSON
        content = json.loads(user_story["content"])

        # 判断是否是数组
        if isinstance(content, list):
            # 如果是数组，每个元素保存为一个文件
            for i, item in enumerate(content, start=1):
                filename = output_dir / f"{user_story['id']}_{i}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)
        else:
            # 如果不是数组，保存为单个文件
            filename = output_dir / f"{user_story['id']}_1.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
