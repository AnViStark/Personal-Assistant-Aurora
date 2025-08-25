from pymongo import MongoClient

class DatabaseHandler():
    def __init__(self):
        client = MongoClient("mongodb://localhost:27017/")
        self.db = client["aurora_db"]
        self.phrases = self.db["phrases"]
        self.user_preferences = self.db["user_preferences"]

    def add_record(self, collection, record:dict):
        try:
            collection.insert_one(record)
            print("Запись добавлена")
        except Exception as e:
            print(str(e))

    def delete_record(self, collection, record:dict):
        try:
            collection.delete_one(record)
            print("Запись удалена")
        except Exception as e:
            print(str(e))

    def get_n_records(self, collection, number):
        try:
            # Возвращаем в правильном порядке: старое → новое
            records = list(collection.find().sort("_id", -1).limit(number))
            return list(reversed(records))
        except Exception as e:
            print(str(e))
            return []
    
    def delete_all_records(self, collection):
        try:
            result = collection.delete_many({})
            print(f"Удалено записей: {result.deleted_count}")
        except Exception as e:
            print(str(e))