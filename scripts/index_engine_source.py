#!/usr/bin/env python3
"""
Extract UE C++ header API comments and index into the knowledge base.
Target: Engine/Plugins/Runtime/GameplayAbilities/Source/

Fully local, zero API cost. Adds to existing ChromaDB collection.
"""

import os
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ENGINE_ROOT = Path(os.environ.get("UE_ENGINE_ROOT", "E:/UE_5.7"))
GAS_SOURCE = ENGINE_ROOT / "Engine/Plugins/Runtime/GameplayAbilities/Source"
CHROMA_DIR = Path(os.environ.get("UE_KB_CHROMA_DIR", str(Path(__file__).resolve().parents[1] / ".chroma_db")))
MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# Additional high-value engine modules to include
EXTRA_MODULES = [
    # Gameplay Framework
    ENGINE_ROOT / "Engine/Source/Runtime/Engine/Public/GameFramework",
    # AI
    ENGINE_ROOT / "Engine/Source/Runtime/AIModule/Public",
    # Animation
    ENGINE_ROOT / "Engine/Source/Runtime/Engine/Public/Animation",
]


def extract_api_docs(file_path: Path) -> list[dict]:
    """Extract /** ... */ doc comments linked to the next declaration."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return []

    rel_path = file_path.relative_to(ENGINE_ROOT) if ENGINE_ROOT in file_path.parents else file_path
    module_name = str(rel_path).replace("\\", "/")

    results = []

    # Pattern: /** ... */ followed by decorators and then the actual declaration.
    # Handle nested parens in UCLASS/USTRUCT/UENUM/UINTERFACE decorators.
    # Use balanced-paren matching instead of [^)]*
    
    # First find all doc comments with their positions
    doc_comments = list(re.finditer(r'/\*\*(.*?)\*/', text, re.DOTALL))
    
    for idx, dc in enumerate(doc_comments):
        doc_text = dc.group(1).strip()
        if not doc_text or len(doc_text) < 20:
            continue
            
        # Look after the */ for the next declaration (skip blank lines and decorators)
        pos = dc.end()
        remaining = text[pos:]
        
        # Skip whitespace and decorators like UCLASS(...), USTRUCT(...), etc.
        while remaining:
            remaining = remaining.lstrip()
            # Check for decorator with balanced parens
            decorator_match = re.match(r'(UCLASS|USTRUCT|UENUM|UINTERFACE|UFUNCTION|UPROPERTY)', remaining)
            if decorator_match:
                # Find matching closing paren
                depth = 0
                i = decorator_match.end()
                while i < len(remaining):
                    if remaining[i] == '(':
                        depth += 1
                    elif remaining[i] == ')':
                        depth -= 1
                        if depth == 0:
                            remaining = remaining[i+1:]
                            break
                    i += 1
                if depth > 0:
                    break  # unbalanced, stop
            else:
                break
        
        # Now check for access specifier or class/struct/enum declaration
        remaining = remaining.lstrip()
        
        # Skip access specifiers (public:/private:/protected:)
        access_match = re.match(r'(public|private|protected)\s*:', remaining)
        if access_match:
            remaining = remaining[access_match.end():].lstrip()
        
        # Check for class/struct/enum declaration
        decl_match = re.match(
            r'(class|struct|enum\s+class|enum)\s+(\w+)(\s*:\s*[^{]+)?\s*\{',
            remaining, re.DOTALL
        )
        
        if decl_match:
            decl_type = decl_match.group(1)
            decl_name = decl_match.group(2)
            base = decl_match.group(3)
            
            # Clean doc text
            cleaned_lines = []
            for line in doc_text.split("\n"):
                line = re.sub(r'^\s*\*\s?', '', line).strip()
                if line:
                    cleaned_lines.append(line)
            cleaned_doc = " ".join(cleaned_lines)
            
            chunk_parts = []
            chunk_parts.append(f"[{decl_type} {decl_name}]")
            if base:
                chunk_parts.append(f"Base: {base.strip()}")
            chunk_parts.append("")
            chunk_parts.append(cleaned_doc)
            
            chunk_text = "\n".join(chunk_parts)
            chunk_id = f"gas:{module_name}:{decl_name}:{idx}"
            
            results.append({
                "text": chunk_text,
                "source": f"engine-source/{module_name}",
                "heading": decl_name,
                "doc_type": decl_type,
                "id": chunk_id,
            })
        else:
            # Maybe it's a standalone /** ... */ comment describing a function
            # Check if it's followed by a function declaration
            func_match = re.match(
                r'(UE_API\s+)?(void|bool|int32|float|FName|FString|UClass\s*\*|AActor\s*\*|APlayerController\s*\*|F\w+)\s+(\w+)\s*\(',
                remaining
            )
            if func_match:
                func_name = func_match.group(3)
                return_type = func_match.group(2)
                
                cleaned_lines = []
                for line in doc_text.split("\n"):
                    line = re.sub(r'^\s*\*\s?', '', line).strip()
                    if line:
                        cleaned_lines.append(line)
                cleaned_doc = " ".join(cleaned_lines)
                
                chunk_text = f"[function] {return_type} {func_name}()\n\n{cleaned_doc}"
                chunk_id = f"gas:{module_name}:func:{func_name}:{idx}"
                
                results.append({
                    "text": chunk_text,
                    "source": f"engine-source/{module_name}",
                    "heading": f"{func_name}()",
                    "doc_type": "function",
                    "id": chunk_id,
                })
            elif len(doc_text) > 500:
                # Large system-level doc comment (e.g. describing the whole system architecture)
                # Keep it as a standalone chunk
                cleaned_lines = []
                for line in doc_text.split("\n"):
                    line = re.sub(r'^\s*\*\s?', '', line).strip()
                    if line:
                        cleaned_lines.append(line)
                cleaned_doc = " ".join(cleaned_lines)
                
                # Generate a unique-ish heading from first meaningful line
                heading = (cleaned_lines[0][:60] if cleaned_lines else "System Overview")
                
                chunk_text = cleaned_doc
                chunk_id = f"gas:{module_name}:system:{idx}"
                
                results.append({
                    "text": chunk_text,
                    "source": f"engine-source/{module_name}",
                    "heading": heading,
                    "doc_type": "overview",
                    "id": chunk_id,
                })

    return results


def scan_modules(roots: list[Path]) -> list[dict]:
    """Scan all .h files in given root directories."""
    all_docs = []
    files_scanned = 0

    for root in roots:
        if not root.exists():
            print(f"  [!] Skipping {root} (not found)")
            continue

        headers = sorted(root.rglob("*.h"))
        # Exclude generated headers
        headers = [h for h in headers if ".generated." not in h.name and "Intermediate" not in str(h)]

        print(f"  [*] Scanning {root.relative_to(ENGINE_ROOT)} ({len(headers)} headers)")

        for hp in headers:
            docs = extract_api_docs(hp)
            if docs:
                all_docs.extend(docs)
            files_scanned += 1

    print(f"\n  [*] Files scanned: {files_scanned}")
    print(f"  [*] API docs extracted: {len(all_docs)}")
    return all_docs


def merge_into_knowledge_base(documents: list[dict]):
    """Add extracted API docs to the existing ChromaDB collection."""
    from sentence_transformers import SentenceTransformer
    import chromadb

    print(f"\n[*] Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection("ue_knowledge")
        before = collection.count()
        print(f"    Collection exists: {before} docs before merge")
    except Exception:
        collection = client.create_collection(name="ue_knowledge")
        before = 0
        print(f"    Created new collection")

    # Filter out already-existing IDs
    existing_ids = set()
    try:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"]) if existing["ids"] else set()
    except:
        pass

    new_docs = [d for d in documents if d["id"] not in existing_ids]
    print(f"\n    New documents to add: {len(new_docs)} (skipped {len(documents) - len(new_docs)} duplicates)")

    if not new_docs:
        print("    Nothing to add.")
        return

    # Batch embed and add
    texts = [d["text"] for d in new_docs]
    ids = [d["id"] for d in new_docs]
    metadatas = [{"source": d["source"], "heading": d["heading"], "doc_type": d["doc_type"]} for d in new_docs]

    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        
        embeddings = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        
        collection.add(
            ids=batch_ids,
            embeddings=embeddings.tolist(),
            documents=batch,
            metadatas=batch_metas
        )

    after = collection.count()
    print(f"\n    Collection now: {after} docs (+{after - before})")


def main():
    import time
    start = time.time()

    print("=" * 60)
    print("  UE Engine Source API Doc Indexer")
    print("  Local · Free · Zero API Cost")
    print("=" * 60)

    # Define scan roots — key engine C++ API modules
    scan_roots = [
        GAS_SOURCE / "GameplayAbilities/Public",          # GAS (already done, skips duplicates)
        ENGINE_ROOT / "Engine/Source/Runtime/Core/Public",           # Core: FString, TArray, FName, etc.
        ENGINE_ROOT / "Engine/Source/Runtime/Engine/Public",         # Engine main API
        ENGINE_ROOT / "Engine/Source/Runtime/AIModule/Public",       # AI: BehaviorTree, EQS, Blackboard
        ENGINE_ROOT / "Engine/Source/Runtime/UMG/Public",            # UMG: Widgets, Panel, Button
        ENGINE_ROOT / "Engine/Source/Runtime/Slate/Public",          # Slate UI framework
        ENGINE_ROOT / "Engine/Source/Runtime/AnimationCore/Public",  # Animation core types
        ENGINE_ROOT / "Engine/Source/Runtime/LevelSequence/Public",  # Cinematics
        ENGINE_ROOT / "Engine/Source/Runtime/MovieScene/Public",     # Sequencer core
        ENGINE_ROOT / "Engine/Source/Runtime/RenderCore/Public",     # Rendering core
        ENGINE_ROOT / "Engine/Source/Runtime/Engine/Public/Animation",  # Animation system
    ]

    # Scan ALL engine headers
    print("\n[*] Phase 1: Scanning engine C++ API headers...")
    docs = scan_modules(scan_roots)

    if not docs:
        print("[!] No docs extracted!")
        sys.exit(1)

    # Merge
    print("\n[*] Phase 2: Merging into knowledge base...")
    merge_into_knowledge_base(docs)

    elapsed = time.time() - start
    print(f"\n[✓] Done! ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
