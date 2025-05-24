
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
import numpy as np

# Define emotion labels
EMOTION_LABELS = [
    "anger", "anticipation", "disgust", "fear", "joy", "love", "optimism", 
    "pessimism", "sadness", "surprise", "trust", "neutral", "excitement",
    "gratitude", "pride", "confusion", "embarrassment", "guilt", "shame",
    "anxiety", "desire", "jealousy", "disappointment", "amusement",
    "contentment", "relief", "boredom", "frustration"
]

# Load model and tokenizer
def load_model():
    try:
        model_dir = os.path.join(os.path.dirname(__file__), "model")
        print(f"Loading model from {model_dir}")
        
        tokenizer = BertTokenizer.from_pretrained(model_dir)
        model = BertForSequenceClassification.from_pretrained(
            model_dir,
            problem_type="multi_label_classification",
            num_labels=len(EMOTION_LABELS)
        )
        
        print("Model and tokenizer loaded successfully")
        return model, tokenizer
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        raise

# Initialize model and tokenizer
model, tokenizer = None, None

def get_model_and_tokenizer():
    global model, tokenizer
    if model is None or tokenizer is None:
        model, tokenizer = load_model()
    return model, tokenizer

def predict_emotions(text):
    """
    Predict emotions from text input
    
    Args:
        text (str): Input text to analyze
        
    Returns:
        dict: Dictionary mapping emotion labels to probabilities
    """
    model, tokenizer = get_model_and_tokenizer()
    
    # Set model to evaluation mode
    model.eval()
    
    # Tokenize input text
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        padding=True, 
        truncation=True, 
        max_length=128
    )
    
    # Make prediction
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        # Apply sigmoid to get probabilities for multi-label classification
        probs = torch.sigmoid(logits)
    
    # Convert to list and map to emotion labels
    probs_list = probs[0].tolist()
    
    # Create dictionary mapping emotions to probabilities
    # Probability threshold for filtering
    emotions_dict = {
        EMOTION_LABELS[i]: round(float(prob), 4) 
        for i, prob in enumerate(probs_list)
          # Filter out low probabilities
    }
    TOP_N = 5
    # Sort by probability (descending)
    sorted_emotions = dict(
        sorted(emotions_dict.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    )
    
    return sorted_emotions

