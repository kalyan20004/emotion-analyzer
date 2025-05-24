"""
Simple script to test MongoDB connection.
Run this script before deploying to verify your connection.
"""
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_mongodb")

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "emotion_analyzer")

if not MONGO_URI:
    logger.error("MONGO_URI environment variable not set")
    exit(1)

async def test_connection():
    try:
        # Print part of the URI for debugging (without credentials)
        uri_parts = MONGO_URI.split('@')
        if len(uri_parts) > 1:
            masked_uri = f"mongodb+srv://****:****@{uri_parts[1]}"
            logger.info(f"Testing connection to: {masked_uri}")
        
        # Create client with modern connection approach
        client = AsyncIOMotorClient(
            MONGO_URI,
            server_api=ServerApi('1'),
            retryWrites=True,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000
        )
        
        # Try to ping the server
        logger.info("Attempting to ping MongoDB server...")
        await client.admin.command('ping')
        logger.info("MongoDB connection successful! 🎉")
        
        # List available databases
        database_names = await client.list_database_names()
        logger.info(f"Available databases: {database_names}")
        
        # Check if our database exists
        if DB_NAME in database_names:
            logger.info(f"Database '{DB_NAME}' found!")
            db = client[DB_NAME]
            
            # List collections
            collection_names = await db.list_collection_names()
            logger.info(f"Collections in {DB_NAME}: {collection_names}")
        else:
            logger.warning(f"Database '{DB_NAME}' not found. It will be created when data is first inserted.")
            
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting MongoDB connection test...")
    success = asyncio.run(test_connection())
    
    if success:
        logger.info("All tests passed! Your MongoDB connection is working properly.")
        exit(0)
    else:
        logger.error("MongoDB connection test failed!")
        exit(1)
