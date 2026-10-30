import argparse
import json
from pathlib import Path

from mem0 import Memory


OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "qwen2.5:3b"
EMBEDDER_MODEL = "nomic-embed-text:latest"

DATABASE_PATH = Path(__file__).resolve().parent / "ghost_memory_persistence_test_db"
COLLECTION_NAME = "ghost_memory_persistence_test"
TEST_USER_ID = "ghost-memory-persistence-test-user"

FACT = "I am building a project called Ghost in the Machine using Python and Flask."
SEARCH_QUERY = (
    "What project is the user building, and which programming language "
    "and web framework are they using?"
)
EXTRACTION_PROMPT = (
    "Extract explicit, stable facts stated by the user in the latest message. "
    "The user explicitly names an ongoing project and its technologies, so save "
    "that as one concise, self-contained memory, preserving the project name "
    "and both technologies. Do not return an empty memory list for this message."
)
REQUIRED_FACT_TERMS = ("ghost in the machine", "python", "flask")


def create_memory() -> Memory:
    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": LLM_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
                "temperature": 0.1,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBEDDER_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": COLLECTION_NAME,
                "path": str(DATABASE_PATH),
            },
        },
    }
    return Memory.from_config(config)


def print_result(label: str, result: object) -> None:
    print(label)
    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))


def get_result_memories(result: object, label: str) -> list[str]:
    if not isinstance(result, dict):
        raise SystemExit(f"FAIL: {label} did not return a result object: {result!r}")

    memories = result.get("results")
    if not isinstance(memories, list):
        raise SystemExit(f"FAIL: {label} has no 'results' list: {result!r}")

    return [
        item["memory"]
        for item in memories
        if isinstance(item, dict) and isinstance(item.get("memory"), str)
    ]


def contains_test_fact(memories: list[str]) -> bool:
    combined = "\n".join(memories).casefold()
    return all(term in combined for term in REQUIRED_FACT_TERMS)


def add_and_check() -> None:
    if DATABASE_PATH.exists():
        raise SystemExit(
            f"Refusing to add to an existing test database: {DATABASE_PATH}\n"
            "Use --verify to check its contents. No files were changed."
        )

    memory = create_memory()
    add_result = memory.add(
        FACT,
        user_id=TEST_USER_ID,
        prompt=EXTRACTION_PROMPT,
    )
    print_result("COMPLETE ADD RESULT:", add_result)

    all_result = memory.get_all(filters={"user_id": TEST_USER_ID})
    print_result("GET_ALL RESULT:", all_result)
    if not contains_test_fact(get_result_memories(all_result, "get_all")):
        raise SystemExit(
            "FAIL: get_all() did not return a memory containing the project name, "
            "Python, and Flask."
        )

    search_result = memory.search(
        SEARCH_QUERY,
        filters={"user_id": TEST_USER_ID},
    )
    print_result("SEARCH RESULT:", search_result)
    if not contains_test_fact(get_result_memories(search_result, "search")):
        raise SystemExit(
            "FAIL: memory.search() did not retrieve a memory containing the "
            "project name, Python, and Flask."
        )

    print(
        "\nPASS: The fact was extracted, stored, and searchable.\n"
        "This process will now exit. Run this script again with --verify "
        "to test persistence in a fresh Python process."
    )


def verify_after_restart() -> None:
    if not DATABASE_PATH.is_dir():
        raise SystemExit(
            f"FAIL: Test database was not found at {DATABASE_PATH}.\n"
            "Run the add phase first."
        )

    memory = create_memory()
    all_result = memory.get_all(filters={"user_id": TEST_USER_ID})
    print_result("GET_ALL RESULT IN VERIFICATION PROCESS:", all_result)
    if not contains_test_fact(get_result_memories(all_result, "get_all")):
        raise SystemExit(
            "FAIL: The fact was not present in Chroma after restarting Python."
        )

    search_result = memory.search(
        SEARCH_QUERY,
        filters={"user_id": TEST_USER_ID},
    )
    print_result("SEARCH RESULT IN VERIFICATION PROCESS:", search_result)
    if not contains_test_fact(get_result_memories(search_result, "search")):
        raise SystemExit(
            "FAIL: The fact could not be retrieved by search after restarting Python."
        )

    print("\nPASS: The fact remained stored and searchable in the new Python process.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test Mem0 fact extraction and Chroma persistence across processes."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the stored fact in a new process instead of adding it.",
    )
    args = parser.parse_args()

    if args.verify:
        verify_after_restart()
    else:
        add_and_check()


if __name__ == "__main__":
    main()
