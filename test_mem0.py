import logging

logging.basicConfig(level=logging.DEBUG)

from mem0 import Memory

config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen2.5:3b",
            "ollama_base_url": "http://localhost:11434",
            "temperature": 0.1,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "ghost_test",
            "path": "./mem0_test_db",
        },
    },
}

try:
    print("Initializing Mem0...")
    memory = Memory.from_config(config)

    print("\nAdding a test memory...")
    result = memory.add(
        "My project is called Ghost in the Machine. "
        "It is a local AI chatbot project.",
        user_id="ghost_test_user",
    )

    result = memory.add(
    "I am visiting Paris.",
    user_id="ghost_test_user",
    infer=False,
    )
    print("Add result:", result)

    
    print("\nTesting a change in memory...")

    update_result = memory.add(
        "I am now visiting London instead of Paris.",
        user_id="ghost_test_user",
    )

    print("New result:", update_result)

    print("\nAll stored memories:")
    all_memories = memory.get_all(
        filters={"user_id": "ghost_test_user"}
    )
    print(all_memories)

    print("\nReading all memories for this user...")
    all_memories = memory.get_all(
    filters={"user_id": "ghost_test_user"}
    )
    print("Stored memories:", all_memories)


    print("\nTest completed. Check whether the project name appears above.")

    
    print("\nSearching memories about the destination...")
 
    results = memory.search(
        "Where is the user visiting now?",
        filters={"user_id": "ghost_test_user"},
    )

    print("Search results:", results)

except Exception as error:
    print("\nTest failed:")
    print(type(error).__name__, error)
