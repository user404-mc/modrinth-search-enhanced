import json
import os
import math

DATA_DIR = "data"
MAX_TOTAL_SIZE_MB = 20        # Ab dieser Größe wird gesplittet
MAX_CHUNK_SIZE_MB = 9        # Zielgröße pro Chunk

def load_existing_projects():
    """Load projects from existing index or single file."""
    index_path = os.path.join(DATA_DIR, "projects_index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        if index["type"] == "single":
            file_path = os.path.join(DATA_DIR, index["file"])
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif index["type"] == "chunks":
            all_projects = []
            for filename in index["files"]:
                chunk_path = os.path.join(DATA_DIR, filename)
                with open(chunk_path, "r", encoding="utf-8") as f:
                    chunk = json.load(f)
                    all_projects.extend(chunk)
            return all_projects
        else:
            raise ValueError("Unknown index type")
    else:
        # Fallback: try projects.json directly
        single_path = os.path.join(DATA_DIR, "projects.json")
        if os.path.exists(single_path):
            with open(single_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            raise FileNotFoundError("No projects_index.json or projects.json found")

def main():
    print("Loading existing project data...")
    projects = load_existing_projects()
    total_projects = len(projects)
    print(f"Loaded {total_projects} projects.")

    # Serialize full list to JSON
    full_json = json.dumps(projects, ensure_ascii=False, indent=2)
    encoded = full_json.encode('utf-8')
    total_size_mb = len(encoded) / (1024 * 1024)
    print(f"Total serialized size: {total_size_mb:.2f} MB")

    if total_size_mb <= MAX_TOTAL_SIZE_MB:
        print(f"Size is <= {MAX_TOTAL_SIZE_MB} MB – keeping as single file.")
        # Ensure a single projects.json exists
        with open(os.path.join(DATA_DIR, "projects.json"), "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        index = {"type": "single", "file": "projects.json"}
        with open(os.path.join(DATA_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        print("Updated projects_index.json to single file.")
        return

    print(f"Size exceeds {MAX_TOTAL_SIZE_MB} MB – splitting into chunks of max {MAX_CHUNK_SIZE_MB} MB each.")
    # Calculate number of chunks: aim for each chunk <= MAX_CHUNK_SIZE_MB
    # Use 90% of the limit to be safe
    max_bytes = MAX_CHUNK_SIZE_MB * 1024 * 1024 * 0.9
    num_chunks = math.ceil(len(encoded) / max_bytes)
    # Ensure at least 1 chunk
    if num_chunks < 1:
        num_chunks = 1
    # Distribute projects evenly across chunks
    chunk_size = math.ceil(total_projects / num_chunks)
    files = []
    for i in range(num_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total_projects)
        chunk = projects[start:end]
        filename = f"projects_{i}.json"
        with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        files.append(filename)
        # Optional: print size of each chunk
        chunk_json = json.dumps(chunk, ensure_ascii=False, indent=2)
        chunk_mb = len(chunk_json.encode('utf-8')) / (1024 * 1024)
        print(f"  Saved chunk {i+1}/{num_chunks} ({len(chunk)} projects, {chunk_mb:.2f} MB) to {filename}")

    index = {"type": "chunks", "chunks": num_chunks, "files": files}
    with open(os.path.join(DATA_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"Updated projects_index.json with {num_chunks} chunks.")

if __name__ == "__main__":
    main()
