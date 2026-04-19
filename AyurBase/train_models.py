import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
import joblib
import warnings
warnings.filterwarnings('ignore')

def train_disease_model():
    print("Loading symptom_to_disease.csv...", flush=True)
    df = pd.read_csv("symptom_to_disease.csv")
    
    # Target and Features
    X = df.drop(columns=['diseases']).values
    y_raw = df['diseases'].values
    
    # Encode Target
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    
    # Save label encoder and symptom list
    joblib.dump(le, 'disease_label_encoder.pkl')
    symptoms = df.drop(columns=['diseases']).columns.tolist()
    joblib.dump(symptoms, 'symptoms_list.pkl')
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training MLPClassifier for Disease Prediction...", flush=True)
    # Using a 2-layer neural network
    model = MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=20, early_stopping=True, random_state=42, verbose=True)
    model.fit(X_train, y_train)
    
    # Evaluate model
    accuracy = model.score(X_test, y_test)
    print(f"DiseasePredictor Accuracy on Test Set: {accuracy:.4f}", flush=True)
        
    # Save the model
    joblib.dump(model, "disease_model.pkl")
    print("Disease Model saved.", flush=True)

def train_remedy_model():
    print("Loading remedy.csv...", flush=True)
    df = pd.read_csv("remedy.csv")
    
    # Fill missing values
    df['Dosha Type'] = df['Dosha Type'].fillna('Unknown')
    df['Gender/Age Relevance'] = df['Gender/Age Relevance'].fillna('All')
    
    le_disease = LabelEncoder()
    le_dosha = LabelEncoder()
    le_gender_age = LabelEncoder()
    
    # Add 'Unknown' to the classes to handle unseen data during inference
    diseases = df['Problem'].tolist() + ['Unknown']
    doshas = df['Dosha Type'].tolist() + ['Unknown']
    genders = df['Gender/Age Relevance'].tolist() + ['Unknown']
    
    le_disease.fit(diseases)
    le_dosha.fit(doshas)
    le_gender_age.fit(genders)
    
    X_disease = le_disease.transform(df['Problem'])
    X_dosha = le_dosha.transform(df['Dosha Type'])
    X_gender_age = le_gender_age.transform(df['Gender/Age Relevance'])
    
    X = np.column_stack((X_disease, X_dosha, X_gender_age))
    y = df['ID'].values
    
    clf = DecisionTreeClassifier(random_state=42, max_depth=15)
    clf.fit(X, y)
    
    joblib.dump(clf, 'remedy_dt_model.pkl')
    joblib.dump({
        'disease': le_disease,
        'dosha': le_dosha,
        'gender_age': le_gender_age
    }, 'remedy_encoders.pkl')
    print("Remedy Decision Tree Model saved.", flush=True)

if __name__ == "__main__":
    train_disease_model()
    train_remedy_model()
    print("All models trained and saved successfully.", flush=True)
