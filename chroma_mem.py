import chromadb
import uuid
from sentence_transformers import SentenceTransformer
from datetime import datetime

last_successful_search_results = []

class ChromaHandler():
    def __init__(self):
        self.model = SentenceTransformer("ai-forever/sbert_large_mt_nlu_ru")
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="preferences",
            metadata={"hnsw:space": "cosine"}  # используем косинусную меру
        )

    def add_record(self, text, category, importance):
        creation_date = datetime.now().strftime("%d.%m.%y")
        embedding = self.model.encode(text, convert_to_numpy=True).tolist()

        # проверка на дубликат
        result = self.collection.query(
            query_embeddings=embedding,
            n_results=1,
        )
        duplicate_threshold = 0.3  # чем меньше, тем строже
        if result["documents"] and len(result["documents"][0]) > 0:
            candidate = result["documents"][0][0]
            score = result["distances"][0][0]
            if score < duplicate_threshold:
                print("Дубликат найден, не добавляю:", candidate)
                return
            print(f"Запись добавлена в chroma: {text}")

        self.collection.add(
            documents=text,
            embeddings=embedding,
            ids=str(uuid.uuid4()),
            metadatas=[{
                "category": category,
                "importance": importance,
                "creation_date": creation_date
            }]
        )
    
    def search_memory(self, query, k=5, threshold=0.7):
        global last_successful_search_results
        query_vec = self.model.encode(query, convert_to_numpy=True).tolist()
        results = self.collection.query(
            query_embeddings=query_vec,
            n_results=k,
            include=["documents", "distances"],
            where={"importance": {"$in": ["high", "medium", "low"]}}
        )

        filtered = []
        for doc, dist in zip(results["documents"][0], results["distances"][0]):
            if dist < threshold:
                filtered.append(doc)

        print(f"Запрос: {query}")
        print(results)

        if filtered:
            print(f"ПРОШЛИ ФИЛЬТР: {filtered}")
        else:
            print(f"НИКТО НЕ ПРОШЕЛ ФИЛЬТР. ИСПОЛЬЗУЮТСЯ ПОСЛЕДНИЕ ПРОШЕДШИЕ: {last_successful_search_results}")

        if filtered:
            last_successful_search_results = filtered
            return filtered
        else:
            return last_successful_search_results


    def get_critical_memories(self):
        results = self.collection.get(
            where={"importance": "critical"}
        )
        print(f'Критические предпочтения: {results.get("documents", [])}')
        return results.get("documents", [])
