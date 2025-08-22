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

        # Поиск дубликатов
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["documents", "distances"]
        )

        duplicate_threshold = 0.3
        if result["documents"] and len(result["documents"][0]) > 0:
            score = result["distances"][0][0]
            if score < duplicate_threshold:
                print("Дубликат найден, не добавляю:", result["documents"][0][0])
                return

        print(f"Запись добавлена в chroma: {text}")
        self.collection.add(
            documents=[text],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[{
                "category": category,
                "importance": importance,
                "creation_date": creation_date
            }]
        )
    
    def search_memory(self, query, k=10, threshold=0.7):
        global last_successful_search_results
        query_vec = self.model.encode(query, convert_to_numpy=True).tolist()
        results = self.collection.query(
            query_embeddings=[query_vec],  # ← должен быть списком векторов
            n_results=k,
            include=["documents", "metadatas", "distances"],  # ← важно: metadatas
            where={"importance": {"$in": ["high", "medium", "low"]}}
        )

        # Проверяем, есть ли результатыы
        if not results["documents"] or len(results["documents"][0]) == 0:
            print("Нет результатов поиска.")
            return last_successful_search_results

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        filtered = []
        for doc, dist, meta, id in zip(documents, distances, metadatas, ids):
            if dist < threshold:  # чем меньше расстояние, тем ближе
                filtered.append({
                    "id": id,
                    "text": doc,
                    "category": meta["category"],
                    "importance": meta["importance"]
                })

        print(f"Запрос: {query}")
        print(f"Результаты: {results}")

        if filtered:
            print(f"ПРОШЛИ ФИЛЬТР: {filtered}")
            last_successful_search_results = filtered
            return filtered
        else:
            print("НИКТО НЕ ПРОШЕЛ ФИЛЬТР. ИСПОЛЬЗУЮТСЯ ПОСЛЕДНИЕ ПРОШЕДШИЕ.")
            return last_successful_search_results


    def get_critical_memories(self):
        results = self.collection.get(
            where={"importance": "critical"}
        )
        print(f'Критические предпочтения: {results.get("documents", [])}')
        return results.get("documents", [])
    
    def delete_record(self, record_id: str):
        try:
            self.collection.delete(ids=[record_id])
            print(f"[Chroma] Удалена запись: {record_id}")
        except Exception as e:
            print(f"[Chroma] Ошибка при удалении записи {record_id}: {e}")
