from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from graph.kg_client import KGClient
import config

llm = ChatOpenAI(
    model="gpt-4o",
    base_url=config.BASE_URL,
    openai_api_key=config.OPENAI_API_KEY,
    temperature=0.7,
)

template = open(config.PROMPT_TEMPLATE_PATH, "r", encoding="utf-8").read()
prompt = PromptTemplate.from_template(template)

story_chain = prompt | llm


def generate_user_stories():
    user_story_list = []
    client = KGClient()
    data = client.get_data()
    for module in data["modules"]:
        for section in data["module_to_sections"][module]:
            section_id = section["section"]
            contents = client.get_contents_in_section(section_id)
            user_story = story_chain.invoke({"user_doc_content": contents})
            user_story_list.append(
                {
                    "id": section_id,
                    "content": user_story.content.replace("```json\n", "")
                    .replace("```", "")
                    .strip(),
                }
            )

    return user_story_list


if __name__ == "__main__":
    client = KGClient()
    data = client.get_data()
    for module in data["modules"]:
        for section in data["module_to_sections"][module]:
            section_id = section["section"]
            if "user settings_preferences" in section_id:
                contents = client.get_contents_in_section(section_id)
                user_story = story_chain.invoke({"user_doc_content": contents})
                print(user_story.content)
