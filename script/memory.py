from collections import defaultdict

MAX_TURNS = 3

conversation_store=defaultdict(list)

def get_memory(user_id: str):
    return conversation_store[user_id]

def add_to_memory(user_id: str, question: str, answer: str):
    conversation_store[user_id].append({
        "question": question,
        "answer": answer
    })

    # keep only last N turns
    conversation_store[user_id] = conversation_store[user_id][-MAX_TURNS:]