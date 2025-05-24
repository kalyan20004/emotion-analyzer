"""
Pydantic schemas for request/response validation and data models.
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

class EmotionRequest(BaseModel):
    """Schema for emotion analysis request"""
    text: str = Field(..., example="I am really happy!")
    
    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v

class EmotionResponse(BaseModel):
    """Schema for emotion analysis response"""
    emotions: Dict[str, float]

class PredictionInDB(BaseModel):
    """Schema for a prediction stored in the database"""
    id: str = Field(alias="_id")
    text: str
    emotions: Dict[str, float]
    timestamp: datetime
    request_info: Optional[Dict[str, Any]] = None
    
    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "text": "I am feeling happy and excited!",
                "emotions": {
                    "joy": 0.92,
                    "excitement": 0.85,
                    "optimism": 0.76
                },
                "timestamp": "2023-04-15T10:30:00.000Z",
                "request_info": {
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0..."
                }
            }
        }

class PredictionResponse(BaseModel):
    """Schema for prediction response from API"""
    id: str
    text: str
    emotions: Dict[str, float]
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "text": "I am feeling happy and excited!",
                "emotions": {
                    "joy": 0.92,
                    "excitement": 0.85,
                    "optimism": 0.76
                },
                "timestamp": "2023-04-15T10:30:00.000Z"
            }
        }

class PredictionList(BaseModel):
    """Schema for a list of predictions"""
    predictions: List[PredictionResponse]
    total: int
    page: int
    limit: int
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "text": "I am feeling happy and excited!",
                        "emotions": {
                            "joy": 0.92,
                            "excitement": 0.85,
                            "optimism": 0.76
                        },
                        "timestamp": "2023-04-15T10:30:00Z"
                    }
                ],
                "total": 42,
                "page": 1,
                "limit": 10
            }
        }

class Stats(BaseModel):
    """Schema for statistics about predictions"""
    total_predictions: int
    top_emotions: List[Dict[str, Any]]
    predictions_by_day: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "total_predictions": 1250,
                "top_emotions": [
                    {"emotion": "joy", "average_score": 0.78, "count": 450},
                    {"emotion": "sadness", "average_score": 0.62, "count": 320}
                ],
                "predictions_by_day": [
                    {"date": "2023-04-14", "count": 42},
                    {"date": "2023-04-15", "count": 56}
                ]
            }
        }

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    
    class Config:
        schema_extra = {
            "example": {
                "detail": "An error occurred while processing your request"
            }
        }