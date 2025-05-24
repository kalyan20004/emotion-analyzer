"""
Modified predict.py to properly load model from Hugging Face
"""
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
import numpy as np
from huggingface_hub import login
import logging
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define emotion labels
EMOTION_LABELS = [
    "anger", "anticipation", "disgust", "fear", "joy", "love", "optimism", 
    "pessimism", "sadness", "surprise", "trust", "neutral", "excitement",
    "gratitude", "pride", "confusion", "embarrassment", "guilt", "shame",
    "anxiety", "desire", "jealousy", "disappointment", "amusement",
    "contentment", "relief", "boredom", "frustration"
]

# Model settings
MODEL_HF_PATH = os.environ.get("MODEL_HF_PATH", "NNKalyan/emotion-analyzer-model")
USE_LOCAL_MODEL = os.environ.get("USE_LOCAL_MODEL", "False").lower() == "true"
HF_TOKEN = os.environ.get("HF_TOKEN", None)
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")

# Model tracking
MODEL_LOADED = False

# Load model and tokenizer
def load_model():
    global MODEL_LOADED
    try:
        # Authenticate with Hugging Face if token is provided
        if HF_TOKEN and not USE_LOCAL_MODEL:
            login(token=HF_TOKEN)
            logger.info("Logged in to Hugging Face Hub")
        
        # Determine model source
        if USE_LOCAL_MODEL:
            model_source = LOCAL_MODEL_DIR
            logger.info(f"Loading model from local path: {model_source}")
        else:
            model_source = MODEL_HF_PATH
            logger.info(f"Loading model from Hugging Face Hub: {model_source}")
        
        # Load tokenizer with fallback mechanism
        try:
            tokenizer = BertTokenizer.from_pretrained(model_source)
            logger.info("Tokenizer loaded successfully")
        except Exception as e:
            logger.warning(f"Error loading tokenizer from {model_source}: {str(e)}")
            # Fallback to default BERT tokenizer if custom one fails
            tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
            logger.info("Loaded fallback tokenizer (bert-base-uncased)")
        
        # Load model
        model = BertForSequenceClassification.from_pretrained(
            model_source,
            problem_type="multi_label_classification",
            num_labels=len(EMOTION_LABELS)
        )
        logger.info("Model loaded successfully")
        
        MODEL_LOADED = True
        return model, tokenizer
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}", exc_info=True)
        MODEL_LOADED = False
        raise

# Initialize model and tokenizer
model, tokenizer = None, None

def get_model_and_tokenizer():
    global model, tokenizer
    if model is None or tokenizer is None:
        logger.info("First-time model loading")
        model, tokenizer = load_model()
    return model, tokenizer

def is_model_loaded():
    """Check if the model has been loaded successfully"""
    return MODEL_LOADED

def predict_emotions(text):
    """
    Predict emotions from text input
    
    Args:
        text (str): Input text to analyze
        
    Returns:
        dict: Dictionary mapping emotion labels to probabilities
    """
    logger.info(f"Predicting emotions for text: {text[:50]}..." if len(text) > 50 else f"Predicting emotions for text: {text}")
    
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
    emotions_dict = {
        EMOTION_LABELS[i]: round(float(prob), 4) 
        for i, prob in enumerate(probs_list)
    }
    
    # Sort by probability (descending) and take top N
    TOP_N = 5
    sorted_emotions = dict(
        sorted(emotions_dict.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    )
    
    logger.info(f"Prediction complete. Top emotions: {sorted_emotions}")
    return sorted_emotions