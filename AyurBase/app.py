from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
import joblib
import pandas as pd
import numpy as np
import os
from config import SEVERE_DISEASES, MONGO_URI, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Setup MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info() # trigger exception if cannot connect
    db = client.ayurbase
    users_collection = db.users
except Exception as e:
    print(f"Warning: Could not connect to MongoDB. Using local dict for testing. Error: {e}")
    db = None
    users_collection = {}

# Load ML Models and Data
print("Loading Models...", flush=True)
try:
    disease_model = joblib.load('disease_model.pkl')
    disease_le = joblib.load('disease_label_encoder.pkl')
    symptoms_list = joblib.load('symptoms_list.pkl')
    
    remedy_model = joblib.load('remedy_dt_model.pkl')
    remedy_encoders = joblib.load('remedy_encoders.pkl')
    
    # Load dataset for querying remedy details and doctors
    remedy_df = pd.read_csv('remedy.csv')
    doctors_df = pd.read_csv('ayurvedic_doctors.csv')
except Exception as e:
    print(f"Warning: Models not loaded. Please wait for train_models.py to finish. Error: {e}")
    disease_model = None

# --- UI ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    if 'user_id' in session:
        return redirect(url_for('checker'))
    return render_template('auth.html')

@app.route('/checker')
def checker():
    if 'user_id' not in session:
        return redirect(url_for('auth'))
    return render_template('checker.html', symptoms=symptoms_list if disease_model else [])

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('auth'))
    return render_template('results.html')

# --- API ROUTES ---

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    age = data.get('age')
    gender = data.get('gender')
    dosha = data.get('dosha', 'Unknown')
    district = data.get('district')
    
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
        
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400
        
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    user_id = users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password,
        "age": age,
        "gender": gender,
        "dosha": dosha,
        "district": district
    }).inserted_id
    
    session['user_id'] = str(user_id)
    return jsonify({"success": True, "message": "User registered successfully"})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
        
    user = users_collection.find_one({"email": email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['user_id'] = str(user['_id'])
        return jsonify({"success": True})
        
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"success": True})

@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session or db is None:
        return jsonify({"error": "Unauthorized"}), 401
    user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
    if user:
        user['_id'] = str(user['_id'])
        del user['password']
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404

def get_age_gender_relevance(age, gender):
    # Simplified mapping for demonstration based on the dataset
    # The dataset has classes like 'All', 'Adults', 'Male-specific', 'Elderly'
    if age and int(age) > 60:
        return "Elderly"
    if age and int(age) > 18:
        if gender and gender.lower() == 'male':
            return "Male-specific" # Note: actual dataset has 'All' or specific strings
        return "Adults"
    return "All"

@app.route('/api/predict', methods=['POST'])
def predict():
    if not disease_model:
        return jsonify({"error": "Models are still training. Please try again later."}), 503
        
    if 'user_id' not in session or db is None:
        return jsonify({"error": "Unauthorized"}), 401
        
    user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
    
    data = request.json
    selected_symptoms = data.get('symptoms', []) # list of strings
    
    if not selected_symptoms or len(selected_symptoms) < 3:
        return jsonify({"error": "Please provide at least 3 symptoms for an accurate prediction."}), 400
        
    # 1. Disease Prediction
    # Create one-hot array
    input_vector = np.zeros(len(symptoms_list))
    for i, s in enumerate(symptoms_list):
        if s in selected_symptoms:
            input_vector[i] = 1
            
    # The MLPClassifier takes 2D array
    pred_idx = disease_model.predict([input_vector])[0]
    predicted_disease = disease_le.inverse_transform([pred_idx])[0]
    
    # Check severity
    is_severe = False
    for severe in SEVERE_DISEASES:
        if severe.lower() in predicted_disease.lower():
            is_severe = True
            break
            
    if is_severe:
        # Fetch nearest doctor based on district
        district = user.get('district', '')
        nearby_doctors = []
        if district:
            # Simple substring match
            docs = doctors_df[doctors_df['District Name'].str.contains(district, case=False, na=False)]
            for _, row in docs.iterrows():
                nearby_doctors.append({
                    "name": row.get('Name', 'Unknown'),
                    "address": row.get('Address', 'Unknown'),
                    "contact": row.get('Contact Number', 'Unknown')
                })
        
        return jsonify({
            "is_severe": True,
            "disease": predicted_disease,
            "message": f"Critical warning: {predicted_disease} is a severe condition. Please contact a doctor immediately. We cannot recommend home remedies for this condition.",
            "doctors": nearby_doctors[:5] # limit to 5
        })
        
    # 2. Remedy Recommendation
    dosha = user.get('dosha', 'Unknown')
    age = user.get('age', 30)
    gender = user.get('gender', 'All')
    gender_age = get_age_gender_relevance(age, gender)
    
    # Handle unseen labels by falling back to 'Unknown'
    def safe_transform(le, val):
        if val in le.classes_:
            return le.transform([val])[0]
        return le.transform(['Unknown'])[0]
        
    x_dis = safe_transform(remedy_encoders['disease'], predicted_disease)
    x_dos = safe_transform(remedy_encoders['dosha'], dosha)
    x_ga = safe_transform(remedy_encoders['gender_age'], gender_age)
    
    remedy_id = remedy_model.predict([[x_dis, x_dos, x_ga]])[0]
    
    # Fetch details from remedy.csv
    remedy_row = remedy_df[remedy_df['ID'] == remedy_id]
    if len(remedy_row) == 0:
        # Fallback if ID not found somehow
        remedy_row = remedy_df.iloc[0]
    else:
        remedy_row = remedy_row.iloc[0]
        
    # Extract feature importances as basic "reasoning"
    importances = remedy_model.feature_importances_
    features = ["Disease", "Dosha Type", "Age/Gender Relevance"]
    dominant_feature = features[np.argmax(importances)]
    
    reasoning = f"Based on our analysis, this remedy was primarily chosen considering your {dominant_feature}."
    if dominant_feature == "Dosha Type":
        reasoning += f" It balances your {dosha} constitution."
        
    return jsonify({
        "is_severe": False,
        "disease": predicted_disease,
        "remedy": remedy_row.get('Remedies', 'Consult doctor'),
        "medicines": remedy_row.get('Medicines', 'N/A'),
        "preventive_advice": remedy_row.get('Preventive Advice', 'Maintain a healthy diet.'),
        "reasoning": reasoning
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
