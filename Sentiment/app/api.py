from flask import Flask, request, jsonify
from predict import predict_emotions
from db import save_prediction  # NEW

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Please provide 'text' field in JSON body"}), 400

    text = data['text']

    try:
        emotions = predict_emotions(text)
        top_emotions = dict(list(emotions.items())[:5])
        
        save_prediction(text, top_emotions)  # NEW

        return jsonify({"emotions": top_emotions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
