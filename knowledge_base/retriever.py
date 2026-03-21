"""
retriever.py
============
Módulo de recuperação de contexto para o FinMentor.

Este módulo é a ponte entre o ChromaDB e o LLM:
1. Recebe uma pergunta do usuário
2. Busca os chunks mais relevantes na base vetorial
3. Retorna o contexto formatado para ser injetado no prompt do LLM

Conceito central: RAG (Retrieval-Augmented Generation)
    Em vez de depender apenas do conhecimento do LLM (que pode alucinar
    dados financeiros), buscamos contexto real da nossa base curada e
    entregamos junto com a pergunta. O LLM responde baseado NESSE contexto.

Uso:
    from retriever import FinMentorRetriever
    
    retriever = FinMentorRetriever()
    context = retriever.get_context("O que é Tesouro Selic?")
    print(context)
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions


# ── Configurações (devem ser iguais ao build_knowledge_base.py) ───────────────
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "finmentor_kb"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    """Representa um chunk recuperado da base de conhecimento."""
    text: str
    topic: str
    filename: str
    relevance_score: float  # 0 a 100 (%)
    chunk_index: int


@dataclass
class RetrievalResult:
    """Resultado completo de uma consulta à base de conhecimento."""
    query: str
    chunks: List[RetrievedChunk]
    formatted_context: str
    has_relevant_content: bool  # False se todos os scores forem baixos


# ── Classe principal ──────────────────────────────────────────────────────────

class FinMentorRetriever:
    """
    Interface de recuperação de conhecimento para o FinMentor.
    
    Responsável por transformar perguntas em linguagem natural
    em contexto relevante da base de conhecimento financeiro.
    """
    
    def __init__(
        self,
        n_results: int = 4,
        min_relevance: float = 30.0,  # % mínimo para considerar relevante
    ):
        """
        Args:
            n_results: Quantos chunks retornar por consulta (mais = mais contexto,
                       mas também mais tokens enviados ao LLM)
            min_relevance: Score mínimo de relevância (0-100%). Chunks abaixo
                          disso são descartados para evitar contexto irrelevante.
        """
        self.n_results = n_results
        self.min_relevance = min_relevance
        self._collection: Optional[chromadb.Collection] = None
        self._client: Optional[chromadb.ClientAPI] = None
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Inicializa conexão com ChromaDB. Falha com mensagem clara se a base não existir."""
        if not CHROMA_DB_DIR.exists():
            raise RuntimeError(
                f"Base de conhecimento não encontrada em '{CHROMA_DB_DIR}'.\n"
                "Execute primeiro: python build_knowledge_base.py"
            )
        
        try:
            self._client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
            
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
            
            self._collection = self._client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_fn,
            )
            
            total = self._collection.count()
            print(f"✅ Base de conhecimento carregada: {total} chunks disponíveis")
            
        except Exception as e:
            raise RuntimeError(
                f"Erro ao conectar à base de conhecimento: {e}\n"
                "Tente executar: python build_knowledge_base.py"
            )
    
    def retrieve(self, query: str) -> RetrievalResult:
        """
        Busca os chunks mais relevantes para uma pergunta.
        
        Args:
            query: Pergunta do usuário em linguagem natural
            
        Returns:
            RetrievalResult com chunks ordenados por relevância e contexto formatado
        """
        if not query.strip():
            return RetrievalResult(
                query=query,
                chunks=[],
                formatted_context="",
                has_relevant_content=False,
            )
        
        # Executa a busca vetorial no ChromaDB
        raw_results = self._collection.query(
            query_texts=[query],
            n_results=self.n_results,
            include=["documents", "metadatas", "distances"],
        )
        
        # Processa os resultados
        chunks = []
        for text, meta, distance in zip(
            raw_results["documents"][0],
            raw_results["metadatas"][0],
            raw_results["distances"][0],
        ):
            # Converte distância cosine em score de relevância (0-100%)
            # Distância 0 = idêntico (100%), distância 2 = oposto (0%)
            relevance = max(0, (1 - distance / 2) * 100)
            
            if relevance >= self.min_relevance:
                chunks.append(RetrievedChunk(
                    text=text,
                    topic=meta.get("topic", "Geral"),
                    filename=meta.get("filename", ""),
                    relevance_score=round(relevance, 1),
                    chunk_index=meta.get("chunk_index", 0),
                ))
        
        # Ordena por relevância (maior primeiro)
        chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        has_relevant = len(chunks) > 0 and chunks[0].relevance_score >= 50.0
        formatted = self._format_context(query, chunks) if chunks else ""
        
        return RetrievalResult(
            query=query,
            chunks=chunks,
            formatted_context=formatted,
            has_relevant_content=has_relevant,
        )
    
    def _format_context(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """
        Formata os chunks recuperados em um contexto estruturado para o LLM.
        
        O formato é importante: o LLM precisa entender que deve se basear
        nesse contexto, não em conhecimento geral potencialmente impreciso.
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Fonte {i} | Tópico: {chunk.topic} | Relevância: {chunk.relevance_score:.0f}%]\n"
                f"{chunk.text}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_context_for_llm(self, query: str) -> str:
        """
        Método simplificado que retorna apenas o contexto formatado como string.
        Ideal para injeção direta no prompt do LLM.
        
        Returns:
            String com contexto ou mensagem padrão se não houver contexto relevante
        """
        result = self.retrieve(query)
        
        if not result.has_relevant_content:
            return (
                "Não foram encontradas informações específicas na base de conhecimento "
                "para esta consulta. Responda com base no seu conhecimento geral sobre "
                "finanças pessoais e investimentos no Brasil, sendo claro sobre as limitações."
            )
        
        return result.formatted_context
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da base de conhecimento."""
        stats_path = CHROMA_DB_DIR / "kb_stats.json"
        if stats_path.exists():
            with open(stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"total_chunks": self._collection.count() if self._collection else 0}


# ── Demonstração interativa ───────────────────────────────────────────────────

def demo_retriever():
    """
    Demonstração do retriever com perguntas reais.
    Execute este arquivo diretamente para ver o retriever em ação.
    """
    print("\n" + "="*60)
    print("  FinMentor Retriever — Demonstração")
    print("="*60)
    
    retriever = FinMentorRetriever(n_results=3, min_relevance=35.0)
    
    # Exibe estatísticas
    stats = retriever.get_stats()
    print(f"\n📊 Base: {stats.get('total_documents', '?')} documentos, "
          f"{stats.get('total_chunks', '?')} chunks")
    print(f"   Tópicos: {', '.join(stats.get('topics', []))}")
    
    # Perguntas de teste com diferentes complexidades
    demo_queries = [
        # Pergunta direta
        "O que é Tesouro Selic e para quem é indicado?",
        # Pergunta sobre perfil
        "Como identificar se sou conservador ou moderado?",
        # Pergunta sobre cálculo
        "Como funciona o imposto de renda sobre CDB?",
        # Pergunta sobre segurança
        "Como saber se um investimento é golpe?",
        # Pergunta fora do escopo (para testar o filtro)
        "Qual o melhor time de futebol do Brasil?",
    ]
    
    for query in demo_queries:
        print(f"\n{'='*60}")
        print(f"❓ Pergunta: {query}")
        print(f"{'='*60}")
        
        result = retriever.retrieve(query)
        
        print(f"📌 Relevante: {'✅ Sim' if result.has_relevant_content else '⚠️  Baixa relevância'}")
        
        if result.chunks:
            print(f"🔍 Top {len(result.chunks)} chunks encontrados:")
            for chunk in result.chunks[:2]:  # Mostra só os 2 melhores
                print(f"\n  [{chunk.relevance_score:.0f}%] {chunk.topic}")
                print(f"  {chunk.text[:200]}...")
        else:
            print("  ℹ️  Nenhum chunk relevante encontrado")


if __name__ == "__main__":
    demo_retriever()
