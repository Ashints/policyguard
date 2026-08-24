from script.retrieval import retrieve

TEST_CASES = [
    {
        "question": "What principles must be followed when processing personal data?",
        "expected_articles": ["article5"]
    },
    {
        "question": "When is processing of personal data lawful?",
        "expected_articles": ["article6"]
    }
]

TOP_K = 5


def evaluate_retrieval():
    passed = 0

    for case in TEST_CASES:
        question = case["question"]
        expected = set(case["expected_articles"])

        results = retrieve(question)

        retrieved_articles = [
            r["article"]
            for r in results[:TOP_K]
        ]

        hit = expected.intersection(retrieved_articles)

        print("\nQuestion:", question)
        print("Expected:", expected)
        print("Retrieved:", retrieved_articles)

        if hit:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")

    total = len(TEST_CASES)

    percentage = (passed / total) * 100

    print("\n==============================")
    print(f"Passed: {passed}/{total}")
    print(f"Recall@{TOP_K}: {percentage:.2f}%")
    print("==============================")


if __name__ == "__main__":
    evaluate_retrieval()