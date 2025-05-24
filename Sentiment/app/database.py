"""
Database module for MongoDB integration with the Emotion Analyzer app.
This module handles all database operations including connection and CRUD operations.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any
from bson import ObjectId
import os
from dotenv import load_dotenv
import ssl

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection string - can be configured via environment variable
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "emotion_analyzer")

# Safety check to prevent hardcoded credentials in logs
if not MONGO_URI:
    logger.error("MONGO_URI environment variable is not set")
    raise ValueError("MONGO_URI environment variable is not set")

# Database and collection names
PREDICTIONS_COLLECTION = "predictions"

# MongoDB client instance
client = None
db = None

async def connect_to_mongodb():
    """Establish connection to MongoDB"""
    global client, db
    try:
        # Don't log the full URI as it contains credentials
        logger.info(f"Connecting to MongoDB cluster...")
        
        # Configure client with proper SSL settings - updated parameters
        client = AsyncIOMotorClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            retryWrites=True,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000
        )
        
        db = client[DB_NAME]
        
        # Ping the database to verify connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes for better performance
        await db[PREDICTIONS_COLLECTION].create_index("timestamp")
        
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global client
    if client:
        logger.info("Closing MongoDB connection")
        client.close()

async def save_prediction(text: str, emotions: Dict[str, float], 
                         request_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Save a prediction to the database
    
    Args:
        text: The input text that was analyzed
        emotions: Dictionary of emotions and their scores
        request_info: Optional dictionary containing request metadata (IP, user-agent, etc.)
        
    Returns:
        The ID of the inserted document
    """
    try:
        prediction_doc = {
            "text": text,
            "emotions": emotions,
            "timestamp": datetime.utcnow(),
        }
        
        # Add request info if provided
        if request_info:
            prediction_doc["request_info"] = request_info
            
        result = await db[PREDICTIONS_COLLECTION].insert_one(prediction_doc)
        prediction_id = str(result.inserted_id)
        logger.info(f"Saved prediction with ID: {prediction_id}")
        return prediction_id
    except Exception as e:
        logger.error(f"Error saving prediction: {str(e)}")
        raise

async def get_predictions(limit: int = 50, skip: int = 0) -> List[Dict]:
    """
    Retrieve predictions from the database with pagination
    
    Args:
        limit: Maximum number of predictions to return
        skip: Number of predictions to skip (for pagination)
        
    Returns:
        List of prediction documents
    """
    try:
        cursor = db[PREDICTIONS_COLLECTION].find().sort("timestamp", -1).skip(skip).limit(limit)
        predictions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for prediction in predictions:
            prediction["_id"] = str(prediction["_id"])
            
        return predictions
    except Exception as e:
        logger.error(f"Error retrieving predictions: {str(e)}")
        raise

async def get_prediction_by_id(prediction_id: str) -> Optional[Dict]:
    """
    Retrieve a specific prediction by ID
    
    Args:
        prediction_id: The ID of the prediction to retrieve
        
    Returns:
        The prediction document or None if not found
    """
    try:
        prediction = await db[PREDICTIONS_COLLECTION].find_one({"_id": ObjectId(prediction_id)})
        if prediction:
            prediction["_id"] = str(prediction["_id"])
        return prediction
    except Exception as e:
        logger.error(f"Error retrieving prediction {prediction_id}: {str(e)}")
        raise

async def delete_prediction(prediction_id: str) -> bool:
    """
    Delete a prediction by ID
    
    Args:
        prediction_id: The ID of the prediction to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        result = await db[PREDICTIONS_COLLECTION].delete_one({"_id": ObjectId(prediction_id)})
        success = result.deleted_count > 0
        if success:
            logger.info(f"Deleted prediction with ID: {prediction_id}")
        else:
            logger.warning(f"No prediction found with ID: {prediction_id}")
        return success
    except Exception as e:
        logger.error(f"Error deleting prediction {prediction_id}: {str(e)}")
        raise

async def get_stats() -> Dict:
    """
    Get statistics about predictions
    
    Returns:
        Dictionary with statistics like total count, top emotions, etc.
    """
    try:
        # Get total count
        total_count = await db[PREDICTIONS_COLLECTION].count_documents({})
        
        # Get top emotions by frequency
        pipeline = [
            # Convert emotions dict to array of key-value pairs
            {"$project": {
                "emotion_pairs": {"$objectToArray": "$emotions"}
            }},
            # Unwind the array to get one document per emotion
            {"$unwind": "$emotion_pairs"},
            # Group by emotion name and calculate statistics
            {"$group": {
                "_id": "$emotion_pairs.k",  # k is the key (emotion name)
                "average_score": {"$avg": "$emotion_pairs.v"},  # v is the value (score)
                "count": {"$sum": 1}
            }},
            # Reshape the output to match expected format
            {"$project": {
                "_id": 0,
                "emotion": "$_id",
                "average_score": 1,
                "count": 1
            }},
            # Sort by count in descending order
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        cursor = db[PREDICTIONS_COLLECTION].aggregate(pipeline)
        top_emotions_list = await cursor.to_list(length=10)
        
        # Get predictions over time (by day)
        pipeline = [
            {"$group": {
                "_id": {
                    "year": {"$year": "$timestamp"},
                    "month": {"$month": "$timestamp"},
                    "day": {"$dayOfMonth": "$timestamp"}
                },
                "count": {"$sum": 1}
            }},
            # Format the date
            {"$project": {
                "_id": 0,
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": {
                            "$dateFromParts": {
                                "year": "$_id.year",
                                "month": "$_id.month",
                                "day": "$_id.day"
                            }
                        }
                    }
                },
                "count": 1
            }},
            {"$sort": {"date": 1}},
            {"$limit": 30}  # Last 30 days
        ]
        
        cursor = db[PREDICTIONS_COLLECTION].aggregate(pipeline)
        predictions_by_day = await cursor.to_list(length=30)
        
        return {
            "total_predictions": total_count,
            "top_emotions": top_emotions_list,
            "predictions_by_day": predictions_by_day
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise