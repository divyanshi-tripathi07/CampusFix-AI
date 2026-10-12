from .ml_pipeline import evaluate_models

if __name__ == "__main__":
    metrics = evaluate_models()
    print(f"trained_examples={metrics['training_examples']}")
    print(f"category_accuracy={metrics['category_accuracy']:.3f}")
    print(f"priority_labels={metrics['priority_labels']}")
