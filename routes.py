from flask import render_template, url_for, flash, redirect, request, jsonify
from roots import app, db, bcrypt
from roots.models import User, History
from flask_login import login_user, current_user, logout_user, login_required

from tensorflow.keras.models import load_model
from tensorflow.keras.applications.efficientnet import preprocess_input
from PIL import Image
import numpy as np
from datetime import datetime
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return redirect(url_for("welcome"))

@app.route("/welcome")
def welcome():
    # if user logged in go to home
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    return render_template("welcome.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # if user logged in go to home
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # if user logged in go to home
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # check duplicates
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("home"))

    return render_template("register.html")
    
@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        new_pass = request.form.get("newPass")
        confirm_pass = request.form.get("confirmPass")

        if not email or not new_pass or not confirm_pass:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("forgot_password"))

        if new_pass != confirm_pass:
            flash("Passwords do not match.", "error")
            return redirect(url_for("forgot_password"))

        # Find the user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No user with that email.", "error")
            return redirect(url_for("forgot_password"))
        
        user.set_password(new_pass)
        db.session.commit()
        
        flash("Password updated successfully!", "success")
        return redirect(url_for("login"))
    
    return render_template("forgot.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("welcome"))

@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/upload")
@login_required
def upload_page():
    return render_template("upload.html")

@app.route("/plant-details")
@login_required
def plant_details_page():
    return render_template("plant-details.html")

@app.route("/history")
@login_required
def history():
    user_history = sorted(current_user.history, key=lambda h: h.time, reverse=True)
    return render_template("history.html", history=user_history)


class_names = [
    "Aglaonema", "Alocasia", "Anthurium", "Aralia", "Aspidistra",
    "Begonia", "Bromeliad", "Calathea", "Caladium", "Ceropegia",
    "Chamaedorea", "Chlorophytum", "Cissus", "Coleus", "Dieffenbachia",
    "Dracaena", "Epipremnum", "Ficus", "Fittonia", "Haworthia",
    "Hoya", "Monstera", "Nephrolepis", "Oxalis", "Peperomia",
    "Philodendron", "Sansevieria", "Schefflera", "Spathiphyllum",
    "Syngonium", "Tradescantia", "Zamioculcas"
]

model = load_model(os.path.join(BASE_DIR, "../houseplants_model.h5"), compile=False)

# --------- AI PREDICT ----------
@app.route("/predict", methods=["POST"])
def predict():
    try:
         
        file = request.files.get("image")
        if not file:
            return "No image uploaded", 400

        filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        
        img = Image.open(filepath).convert("RGB").resize((224, 224))
        img = np.array(img, dtype=np.float32) / 255.0
        img = np.expand_dims(img, axis=0)

         
        pred = model.predict(img)
        class_index = int(np.argmax(pred))
        plant_name = class_names[class_index]

        
        history_entry = History(
            plant=plant_name,
            image_path=f"static/uploads/{filename}",
            time=datetime.now(),
            user_id=current_user.id  # <--- save for logged-in user
        )

        db.session.add(history_entry)
        db.session.commit()

        return plant_name

    except Exception as e:
        print(e)
        return "Error occurred", 500
