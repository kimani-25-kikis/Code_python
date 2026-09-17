import random

QUESTIONS = [
    ("What keyword defines a function?", "def"),
    ("What's the output of len('hello')?", "5"),
    ("Which type is immutable: list or tuple?", "tuple"),
    ("What does PEP stand for?", "python enhancement proposal"),
    ("What symbol starts a comment?", "#"),
]

def run():
    qs = QUESTIONS[:]
    random.shuffle(qs)
    score = 0
    for i, (q, a) in enumerate(qs, 1):
        print(f"\nQ{i}: {q}")
        user = input("> ").strip().lower()
        if user == a.lower():
            print("Correct!")
            score += 1
        else:
            print(f"Wrong. Answer: {a}")
    print(f"\nScore: {score}/{len(qs)}")
    print("Great!" if score == len(qs) else "Keep practicing.")

if __name__ == "__main__":
    run()