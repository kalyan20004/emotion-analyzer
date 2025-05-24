"""
Flask Main Application for Emotion Analyzer
Full-stack Flask application with templates and static files
"""
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from app.predict import predict_emotions, is_model_loaded
from app.database import (
    connect_to_mongodb, close_mongodb_connection, 
    save_prediction, get_predictions, get_prediction_by_id, 
    delete_prediction, get_stats
)
import logging
import json
import asyncio
import threading
from typing import Optional, List
from datetime import datetime
import os
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# CORS configuration
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000", 
    "http://127.0.0.1:5000",
])

# Database connection status
DB_CONNECTED = False

# Global event loop for async operations
_event_loop = None
_loop_thread = None

def init_event_loop():
    """Initialize a dedicated event loop in a separate thread"""
    global _event_loop, _loop_thread
    
    def run_loop():
        global _event_loop
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
        _event_loop.run_forever()
    
    _loop_thread = threading.Thread(target=run_loop, daemon=True)
    _loop_thread.start()
    
    # Wait a bit for the loop to be ready
    import time
    time.sleep(0.1)

def run_async(coro):
    """
    Helper to run async functions in sync Flask context
    Uses the dedicated event loop thread
    """
    global _event_loop
    
    if _event_loop is None or _event_loop.is_closed():
        logger.error("Event loop is not available")
        raise Exception("Event loop is not available")
    
    try:
        # Schedule the coroutine in the dedicated event loop
        future = asyncio.run_coroutine_threadsafe(coro, _event_loop)
        return future.result(timeout=30)  # 30 second timeout
    except concurrent.futures.TimeoutError:
        logger.error("Async operation timed out")
        raise Exception("Database operation timed out")
    except Exception as e:
        logger.error(f"Error running async operation: {str(e)}")
        raise

# Initialize event loop
init_event_loop()

# Initialize database connection
def init_db():
    """Initialize database connection"""
    global DB_CONNECTED
    try:
        run_async(connect_to_mongodb())
        DB_CONNECTED = True
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        DB_CONNECTED = False

# Initialize database on startup
init_db()

# Helper function to get request info
def get_request_info():
    """Extract useful information from the request"""
    return {
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent"),
        "referer": request.headers.get("Referer")
    }

# Routes

@app.route('/')
def index():
    """Main page - render the emotion analyzer interface"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict_emotion():
    """
    API endpoint to predict emotions from text input
    Accepts both JSON API calls and form submissions
    """
    # Handle JSON requests (API calls)
    if request.is_json:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Please provide 'text' field in JSON body"}), 400
        text = data['text'].strip()
    else:
        # Handle form submissions
        text = request.form.get('text', '').strip()
        if not text:
            flash('Please enter some text to analyze', 'error')
            return redirect(url_for('index'))
    
    # Validate input
    if not text:
        error_msg = "Input text cannot be empty"
        if request.is_json:
            return jsonify({"error": error_msg}), 400
        else:
            flash(error_msg, 'error')
            return redirect(url_for('index'))
    
    if len(text) > 512:
        error_msg = "Input text too long. Max 512 characters allowed"
        if request.is_json:
            return jsonify({"error": error_msg}), 400
        else:
            flash(error_msg, 'error')
            return redirect(url_for('index'))

    logger.info(f"Processing text: {text[:50]}..." if len(text) > 50 else f"Processing text: {text}")

    try:
        # Get emotion predictions
        emotions = predict_emotions(text)
        logger.info(f"Prediction successful: {json.dumps(dict(list(emotions.items())[:3]))}")
        
        # Store prediction in database if connected
        if DB_CONNECTED:
            try:
                request_info = get_request_info()
                prediction_id = run_async(save_prediction(text, emotions, request_info))
                logger.info(f"Saved prediction with ID: {prediction_id}")
            except Exception as e:
                logger.error(f"Error saving prediction: {str(e)}")
                # Don't fail the entire request if database save fails
        
        # Return response based on request type
        if request.is_json:
            return jsonify({"emotions": emotions})
        else:
            # For form submissions, redirect to results page with data
            return render_template('index.html', 
                                 text=text, 
                                 emotions=emotions,
                                 success=True)
            
    except Exception as e:
        error_msg = f"Prediction error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('index'))

@app.route('/api/predictions')
def list_predictions():
    """API endpoint to get list of predictions with pagination"""
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 10)), 100)
    
    if not DB_CONNECTED:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        skip = (page - 1) * limit
        predictions = run_async(get_predictions(limit=limit, skip=skip))
        
        # Format predictions for JSON response
        formatted_predictions = []
        for p in predictions:
            formatted_predictions.append({
                "id": p["_id"],
                "text": p["text"],
                "emotions": p["emotions"],
                "timestamp": p["timestamp"].isoformat() if isinstance(p["timestamp"], datetime) else p["timestamp"]
            })
        
        return jsonify({
            "predictions": formatted_predictions,
            "total": len(formatted_predictions) + skip,  # Simplified
            "page": page,
            "limit": limit
        })
    except Exception as e:
        logger.error(f"Error retrieving predictions: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/predictions/<prediction_id>')
def get_prediction(prediction_id):
    """API endpoint to get a specific prediction by ID"""
    if not DB_CONNECTED:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        prediction = run_async(get_prediction_by_id(prediction_id))
        if not prediction:
            return jsonify({"error": f"Prediction with ID {prediction_id} not found"}), 404
        
        return jsonify({
            "id": prediction["_id"],
            "text": prediction["text"],
            "emotions": prediction["emotions"],
            "timestamp": prediction["timestamp"].isoformat() if isinstance(prediction["timestamp"], datetime) else prediction["timestamp"]
        })
    except Exception as e:
        logger.error(f"Error retrieving prediction {prediction_id}: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/predictions/<prediction_id>', methods=['DELETE'])
def remove_prediction(prediction_id):
    """API endpoint to delete a prediction by ID"""
    if not DB_CONNECTED:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        success = run_async(delete_prediction(prediction_id))
        if not success:
            return jsonify({"error": f"Prediction with ID {prediction_id} not found"}), 404
        
        return jsonify({"message": f"Prediction {prediction_id} deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting prediction {prediction_id}: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/stats')
def get_statistics():
    """API endpoint to get statistics about predictions"""
    if not DB_CONNECTED:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        stats = run_async(get_stats())
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard page to view predictions and statistics"""
    if not DB_CONNECTED:
        flash('Database not connected. Some features may not be available.', 'warning')
        return render_template('dashboard.html', predictions=[], stats={})
    
    try:
        # Get recent predictions
        predictions = run_async(get_predictions(limit=20))
        # Get statistics
        stats = run_async(get_stats())
        
        return render_template('dashboard.html', 
                             predictions=predictions, 
                             stats=stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', predictions=[], stats={})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_status": "loaded" if is_model_loaded() else "not_loaded",
        "database": "connected" if DB_CONNECTED else "disconnected"
    })

@app.route('/api/model-test')
def test_model():
    """Endpoint to test if the model is working"""
    try:
        test_result = predict_emotions("Test message")
        return jsonify({
            "status": "model working",
            "results": test_result
        })
    except Exception as e:
        logger.error(f"Model test failed: {str(e)}")
        return jsonify({"error": f"Model test failed: {str(e)}"}), 503

# Error handlers
@app.errorhandler(404)
def not_found(error):
    if request.is_json:
        return jsonify({"error": "Endpoint not found"}), 404
    # Simple 404 response without template
    return "<h1>404 - Page Not Found</h1><p>The requested page could not be found.</p>", 404

@app.errorhandler(500)
def internal_error(error):
    if request.is_json:
        return jsonify({"error": "Internal server error"}), 500
    # Simple 500 response without template
    return "<h1>500 - Internal Server Error</h1><p>Something went wrong on our end.</p>", 500

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests"""
    return '', 204  # No content response

# Cleanup on shutdown
@app.teardown_appcontext
def close_db(error):
    """Close database connection when app context tears down"""
    pass  # Let the database handle its own cleanup

# Graceful shutdown
import atexit

def cleanup():
    """Cleanup resources on app shutdown"""
    global _event_loop, _loop_thread
    
    # Close database connections
    try:
        if _event_loop and not _event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(close_mongodb_connection(), _event_loop)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    # Stop the event loop
    if _event_loop and not _event_loop.is_closed():
        _event_loop.call_soon_threadsafe(_event_loop.stop)

atexit.register(cleanup)

if __name__ == "__main__":
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host="0.0.0.0", port=port, debug=debug)
