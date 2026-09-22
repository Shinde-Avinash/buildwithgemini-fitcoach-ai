"""Script to create a serverless Vertex AI RAG corpus and import Gutenberg Herbal text."""

import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"
LOCATION = "us-central1"  # Serverless is us-central1
GCS_PATH = "gs://fitcoach-ai-assets-qwiklabs-gcp-01-426fafba1fca/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, remedies, and herbal recipes described in this text. "
    "Ignore and omit all metadata, boilerplate, and publishing notes. "
    "Output clean, self-contained prose."
)

def main():
    print(f"Initializing Vertex AI RAG in {PROJECT_ID} ({LOCATION})...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Update RAG engine config to Serverless mode
    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    print("Configuring RAG Engine for Serverless mode...")
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )

    # 2. Create the RAG Corpus
    print("Creating RAG Corpus 'herbal-fitness-corpus'...")
    corpus = rag.create_corpus(
        display_name="herbal-fitness-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    print(f"✅ RAG Corpus created: {corpus.name}")

    # 3. Import and index documents
    print(f"Importing and indexing {GCS_PATH}...")
    resp = rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT
        ),
    )
    print(f"✅ Import complete. Imported RAG files count: {resp.imported_rag_files_count}")
    print(f"\nCorpus Name to save: {corpus.name}")

if __name__ == "__main__":
    main()
