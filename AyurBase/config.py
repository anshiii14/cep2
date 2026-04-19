import os

# Manual list of severe diseases that require immediate medical attention.
SEVERE_DISEASES = [
    "Heart attack",
    "Stroke",
    "Cancer",
    "Tuberculosis",
    "HIV/AIDS",
    "Chronic kidney disease",
    "Severe Asthma",
    "Pneumonia",
    "Sepsis",
    "Meningitis",
    "Epilepsy (Apasmaram)", # From remedy.csv
    "Parkinson-like symptoms", # From remedy.csv
    "Venereal Diseases", # From remedy.csv
    "Hemorrhoids (Arshas) - variant 11",
    "Hernia",
]

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/ayurbase")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-ayurveda-key")
