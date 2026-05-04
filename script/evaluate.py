from script.retrieval import retrieve
TEST_CASES=[
    {
        "question":"What principles must be followed when processing personal data?",
        "expected_articles": ["Gdpr Article5"]
    },
    {
        "question": "When is processing of personal data lawful?",
        "expected_articles": ["Gdpr Article6"]

    }
]

TOP_K = 5

def evaluate_retrieval():
    passed = 0

    for case in TEST_CASES:
        question = case["question"]
        expected = set(case["expected_articles"])

        results = retrieve(question)
        retrieved_articles = {
            r["article"] for r in results[:TOP_K]
        }
        hit = expected.intersection(retrieved_articles)

        print("\nQuestion:", question)
        print("Expected:", expected)
        print("Retrieved:", retrieved_articles)

        if hit:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")

    print(f"\nScore: {passed}/{len(TEST_CASES)} passed")

if __name__ == "__main__":
    evaluate_retrieval()    