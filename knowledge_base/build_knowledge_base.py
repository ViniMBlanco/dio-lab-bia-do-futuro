"""
build_knowledge_base.py
=======================
Script responsável por:
1. Carregar os documentos financeiros da pasta /documents
2. Dividir em chunks (pedaços menores) para melhor recuperação
3. Gerar embeddings usando sentence-transformers (100% gratuito, local)
4. Armazenar no ChromaDB para consultas futuras

Como usar:
    python build_knowledge_base.py

Dependências (instale com pip):
    pip install chromadb sentence-transformers langchain langchain-community
"""

import os
import json
from pathlib import Path
from typing import List, Dict

# ── Imports principais ──────────────────────────────────────────────────────
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Configurações ────────────────────────────────────────────────────────────
DOCUMENTS_DIR = Path(__file__).parent / "documents"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "finmentor_kb"

# Modelo de embedding gratuito e leve — roda localmente, sem API key
# Alternativas:
#   "paraphrase-multilingual-MiniLM-L12-v2"  → melhor suporte PT-BR
#   "all-MiniLM-L6-v2"                        → mais rápido, só inglês
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Configurações de chunking
# chunk_size: tamanho máximo de cada pedaço (em caracteres)
# chunk_overlap: quantos caracteres se repetem entre chunks vizinhos
#   → overlap é crucial: garante que contexto não seja cortado no meio
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


# ── Funções auxiliares ───────────────────────────────────────────────────────

def load_documents() -> List[Dict]:
    """
    Carrega todos os arquivos .md da pasta de documentos.
    Retorna lista de dicts com 'content', 'filename' e 'topic'.
    """
    documents = []
    md_files = sorted(DOCUMENTS_DIR.glob("*.md"))
    
    if not md_files:
        raise FileNotFoundError(
            f"Nenhum arquivo .md encontrado em {DOCUMENTS_DIR}. "
            "Verifique se os documentos foram criados corretamente."
        )
    
    print(f"📚 Encontrados {len(md_files)} documentos:")
    for file_path in md_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extrai o tópico do nome do arquivo (remove número e extensão)
        topic = file_path.stem.split("_", 1)[1].replace("_", " ").title()
        
        documents.append({
            "content": content,
            "filename": file_path.name,
            "topic": topic,
        })
        print(f"  ✅ {file_path.name} ({len(content):,} caracteres)")
    
    return documents


def chunk_documents(documents: List[Dict]) -> List[Dict]:
    """
    Divide os documentos em chunks menores usando estratégia recursiva.
    
    Por que RecursiveCharacterTextSplitter?
    - Tenta dividir por parágrafos primeiro (\\n\\n)
    - Se ainda for grande, divide por linhas (\\n)
    - Por último, divide por caracteres
    Isso preserva a coerência semântica do texto.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "---", ". ", " ", ""],
        length_function=len,
    )
    
    chunks = []
    for doc in documents:
        raw_chunks = splitter.split_text(doc["content"])
        
        for i, chunk_text in enumerate(raw_chunks):
            # Ignora chunks muito pequenos (menos de 50 chars = provavelmente ruído)
            if len(chunk_text.strip()) < 50:
                continue
            
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {
                    "filename": doc["filename"],
                    "topic": doc["topic"],
                    "chunk_index": i,
                    "total_chunks": len(raw_chunks),
                }
            })
    
    return chunks


def build_chroma_collection(chunks: List[Dict]) -> chromadb.Collection:
    """
    Cria (ou recria) a coleção ChromaDB com os chunks e seus embeddings.
    
    ChromaDB é um banco de dados vetorial local — armazena textos e seus
    vetores numéricos (embeddings) para busca semântica eficiente.
    """
    # Inicializa o cliente ChromaDB com persistência em disco
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    
    # Configura a função de embedding com sentence-transformers
    # huggingface_ef baixa o modelo na primeira execução (~90MB)
    print(f"\n🤖 Carregando modelo de embedding: {EMBEDDING_MODEL}")
    print("  (Primeira execução pode demorar alguns minutos para download)")
    
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    
    # Remove coleção existente para recriar do zero
    # (útil quando os documentos são atualizados)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  ⚠️  Coleção '{COLLECTION_NAME}' existente removida para recriação")
    except Exception:
        pass  # Coleção não existia, tudo bem
    
    # Cria a nova coleção
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=sentence_transformer_ef,
        metadata={
            "description": "Base de conhecimento financeiro FinMentor",
            "language": "pt-BR",
            "embedding_model": EMBEDDING_MODEL,
        }
    )
    
    return collection, client


def populate_collection(collection: chromadb.Collection, chunks: List[Dict]) -> None:
    """
    Insere todos os chunks na coleção ChromaDB.
    O ChromaDB calcula automaticamente os embeddings usando a função configurada.
    """
    print(f"\n📥 Inserindo {len(chunks)} chunks na base vetorial...")
    
    # Prepara os dados para inserção em lote
    ids = [f"chunk_{i:04d}" for i in range(len(chunks))]
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    
    # Insere em lotes de 50 para evitar sobrecarga de memória
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_texts = texts[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]
        
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )
        
        progress = min(i + batch_size, len(chunks))
        print(f"  📊 {progress}/{len(chunks)} chunks inseridos...", end="\r")
    
    print(f"  ✅ {len(chunks)} chunks inseridos com sucesso!          ")


def save_stats(chunks: List[Dict], documents: List[Dict]) -> None:
    """Salva estatísticas da base de conhecimento para referência."""
    stats = {
        "total_documents": len(documents),
        "total_chunks": len(chunks),
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "topics": [doc["topic"] for doc in documents],
        "chunks_per_topic": {}
    }
    
    for chunk in chunks:
        topic = chunk["metadata"]["topic"]
        stats["chunks_per_topic"][topic] = stats["chunks_per_topic"].get(topic, 0) + 1
    
    stats_path = CHROMA_DB_DIR / "kb_stats.json"
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Estatísticas salvas em: {stats_path}")


def test_retrieval(collection: chromadb.Collection) -> None:
    """
    Testa a base com algumas consultas de exemplo.
    Demonstra como a busca semântica funciona na prática.
    """
    test_queries = [
        "O que é Tesouro Selic?",
        "Como investir sendo conservador?",
        "Quero saber sobre juros compostos",
        "Diferença entre CDB e LCI",
        "O que é FII e como funciona?",
    ]
    
    print("\n🧪 Testando recuperação semântica:")
    print("=" * 60)
    
    for query in test_queries:
        results = collection.query(
            query_texts=[query],
            n_results=2,  # Top 2 chunks mais relevantes
            include=["documents", "metadatas", "distances"],
        )
        
        print(f"\n❓ Query: '{query}'")
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            relevance = (1 - dist) * 100  # Converte distância em % de relevância
            print(f"  [{i+1}] Tópico: {meta['topic']} | Relevância: {relevance:.1f}%")
            print(f"      Trecho: {doc[:120]}...")


# ── Função principal ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FinMentor — Construtor de Base de Conhecimento")
    print("=" * 60)
    
    # 1. Carrega os documentos markdown
    documents = load_documents()
    
    # 2. Divide em chunks com overlap
    print(f"\n✂️  Dividindo documentos em chunks (tamanho={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_documents(documents)
    print(f"  ✅ {len(chunks)} chunks gerados no total")
    
    # 3. Cria a coleção ChromaDB
    collection, client = build_chroma_collection(chunks)
    
    # 4. Popula com os chunks + embeddings
    populate_collection(collection, chunks)
    
    # 5. Salva estatísticas
    save_stats(chunks, documents)
    
    # 6. Testa a recuperação
    test_retrieval(collection)
    
    print("\n" + "=" * 60)
    print("  ✅ Base de conhecimento construída com sucesso!")
    print(f"  📂 Localização: {CHROMA_DB_DIR}")
    print("  🚀 Próximo passo: execute o retriever.py para consultar a base")
    print("=" * 60)


if __name__ == "__main__":
    main()
