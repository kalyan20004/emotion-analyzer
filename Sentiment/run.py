from app.predict import predict_emotions

def test_prediction():
    # Test samples
    samples = [
        "I am really happy and excited about this new project!",
        "I'm feeling sad and disappointed after receiving the news.",
        "The loud noise scared me, but I'm feeling better now."
    ]
    
    print("Testing emotion prediction model...")
    
    for sample in samples:
        print("\nInput text:", sample)
        try:
            emotions = predict_emotions(sample)
            print("Predicted emotions:")
            
            # Print top 5 emotions
            for i, (emotion, probability) in enumerate(list(emotions.items())[:5]):
                print(f"  {emotion}: {probability:.4f}")
        except Exception as e:
            print(f"Error during prediction: {str(e)}")

if __name__ == "__main__":
    test_prediction()