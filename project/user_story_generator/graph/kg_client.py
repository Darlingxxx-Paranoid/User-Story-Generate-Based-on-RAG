from typing import List, Dict, Any
from langchain_neo4j import Neo4jGraph
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import config


class KGClient:
    def __init__(self):
        """Initialize the KGClient with Neo4j connection."""
        self.graph = Neo4jGraph(
            url=config.NEO4J_URI,
            username=config.NEO4J_USER,
            password=config.NEO4J_PASSWORD,
        )

    def get_all_modules(self) -> List[str]:
        """Get all module names from the knowledge graph.

        Returns:
            List of module names.
        """
        query = """
        MATCH (m:Module)
        RETURN m.id AS module
        """
        results = self.graph.query(query)
        return [record["module"] for record in results]

    def get_sections_in_module(self, module_name: str) -> List[Dict[str, str]]:
        """Get all sections in a specific module.

        Args:
            module_name: Name of the module to query.

        Returns:
            List of dictionaries containing section names and descriptions.
        """
        query = """
        MATCH (m:Module {id: $module_name})-[:HAS_SECTION]->(s:Section)
        RETURN s.id AS section
        """
        results = self.graph.query(query, {"module_name": module_name})
        return [
            {"section": record["section"].replace("\u200b", "")} for record in results
        ]

    def get_contents_in_section(self, section_id: str):
        section_query = """
        MATCH (s:Section {id: $section_id})
        RETURN s.content AS content
        """
        section_result = self.graph.query(section_query, {"section_id": section_id})

        # Get the section content
        section_content = section_id + "\n" + section_result[0]["content"]

        # Query to get the content of related Webshot examples
        webshot_query = """
        MATCH (s:Section {id: $section_id})-[:HAS_WEBSHOT_EXAMPLE]->(w:Webshot)
        RETURN w.content AS content
        """
        webshot_results = self.graph.query(webshot_query, {"section_id": section_id})

        # Concatenate all Webshot contents
        webshot_contents = " ".join([record["content"] for record in webshot_results])

        # Combine section content with Webshot contents
        full_content = section_content + " " + webshot_contents

        return full_content.strip()

    def get_cross_module_links(self) -> List[Dict[str, str]]:
        """Get all cross-module links between sections and modules.

        Returns:
            List of dictionaries containing link information.
        """
        query = """
        MATCH (s:Section)-[:CALL]->(m:Module)
        RETURN s.id AS section, m.id AS target_module
        """
        results = self.graph.query(query)
        return [
            {
                "section": record["section"].replace("\u200b", ""),
                "target_module": record["target_module"],
            }
            for record in results
        ]

    def get_all_sections(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all sections from all modules.

        Returns:
            Dictionary mapping module names to lists of sections and their descriptions.
        """
        module_to_sections = {}
        modules = self.get_all_modules()
        for module in modules:
            sections = self.get_sections_in_module(module)
            module_to_sections[module] = sections
        return module_to_sections

    def get_data(self):
        data = {
            "modules": self.get_all_modules(),
            "module_to_sections": self.get_all_sections(),
            "links": self.get_cross_module_links(),
        }

        return data


if __name__ == "__main__":
    # Example usage
    client = KGClient()
    print("user settings_preferences​")
