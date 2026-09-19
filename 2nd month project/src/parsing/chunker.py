"""
Text chunking abstraction preserving metadata for RAG and search.
"""

from typing import List, Dict, Any, Optional
from src.config import settings

def recursive_split_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Split text recursively by paragraphs, sentences, words, keeping chunk size within target.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    if not text:
        return []

    # Find the appropriate separator
    chosen_sep = separators[-1]
    for sep in separators:
        if sep in text:
            chosen_sep = sep
            break

    splits = text.split(chosen_sep) if chosen_sep else list(text)

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for split in splits:
        piece = split + chosen_sep if chosen_sep else split
        piece_len = len(piece)

        if current_length + piece_len <= chunk_size:
            current_chunk.append(piece)
            current_length += piece_len
        else:
            if current_chunk:
                merged = "".join(current_chunk).strip()
                if merged:
                    chunks.append(merged)
                
                # Keep overlap pieces
                overlap_chunk: List[str] = []
                overlap_len = 0
                for prev in reversed(current_chunk):
                    if overlap_len + len(prev) <= chunk_overlap:
                        overlap_chunk.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current_chunk = overlap_chunk
                current_length = overlap_len

            # If a single piece exceeds chunk_size, recursively subdivide with next separators
            if piece_len > chunk_size and len(separators) > 1:
                sub_seps = separators[separators.index(chosen_sep) + 1 :]
                sub_chunks = recursive_split_text(split, chunk_size, chunk_overlap, sub_seps)
                chunks.extend(sub_chunks)
            else:
                current_chunk.append(piece)
                current_length += piece_len

    if current_chunk:
        merged = "".join(current_chunk).strip()
        if merged:
            chunks.append(merged)

    return chunks

def split_into_chunks(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Splits text into chunks preserving rich metadata.
    """
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP
    meta = metadata.copy() if metadata else {}
    source_name = meta.get("filename", "unknown_source")

    raw_chunks = recursive_split_text(text, chunk_size=size, chunk_overlap=overlap)

    chunk_objects: List[Dict[str, Any]] = []
    for idx, chunk_text in enumerate(raw_chunks):
        chunk_id = f"{source_name}_chunk_{idx}"
        chunk_meta = {
            **meta,
            "chunk_index": idx,
            "chunk_id": chunk_id,
            "total_chunks": len(raw_chunks),
            "char_length": len(chunk_text),
        }
        chunk_objects.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "metadata": chunk_meta,
        })

    return chunk_objects
