import firebase_admin
from datetime import timezone, datetime
import traceback, os
from fastapi import FastAPI, Request, Query, Cookie, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth, firestore
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from PIL import Image
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from collections import defaultdict
import requests

load_dotenv()

if not firebase_admin._apps:
    cred = credentials.Certificate("cerebrumal-firebase-adminsdk-fbsvc-82c52971a9.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def verify_firebase_password(email, password):
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={os.getenv('FIREBASE_API_KEY')}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        print(f"Firebase password verification - Email: {email}")
        response = requests.post(url, json=payload)
        print(f"Firebase response status: {response.status_code}")
        print(f"Firebase response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Firebase password verification error: {e}")
        return False


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Or ["http://localhost:8000"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()

# ✅ Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ✅ Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def sign_in(request: Request):
    return templates.TemplateResponse("sign-in.html", {"request": request})

@app.get("/patient-list", response_class=HTMLResponse)
async def patient_list(request: Request, session_token: str = Cookie(None)):
    if not session_token:
        print("No available session found.")
        return RedirectResponse(url="/")
    
    # Result part
    result_mapping = {}
    result_ref_list = db.collection("results").stream()
    for result_doc in result_ref_list:
        result_data = result_doc.to_dict()
        patient_id = result_data["patient_id"]
        if patient_id not in result_mapping:
            result_mapping[patient_id] = []
        scanned_on = result_data["scanned_on"]
        if isinstance(scanned_on, DatetimeWithNanoseconds):
            scanned_on = datetime.fromtimestamp(scanned_on.timestamp())
        if scanned_on:
            result_mapping[patient_id].append(scanned_on)

    patient_ref_list= db.collection("patient").stream()
    patients = []
    counter = 0
    for patient_doc in patient_ref_list:
        patient_data = patient_doc.to_dict()  
    
        if patient_data["doctor"] != session_token:
            continue

        if patient_doc.id in result_mapping:
            result_mapping[patient_doc.id].sort(reverse = True)
            result = result_mapping[patient_doc.id][0].strftime("%d/%m/%Y %H:%M:%S")
        else:
            result = "No scan made"
  
        counter += 1
        patients.append({
            "id": patient_doc.id,
            "order": counter,
            "name": patient_data["name"],
            "surname": patient_data["surname"],
            "last_scan": result
        })

    return templates.TemplateResponse("patient-list.html", {"request": request, "patients": patients})

@app.api_route("/scan-mri", methods=["GET", "POST"], response_class=HTMLResponse)
async def scan(request: Request, session_token: str = Cookie(None), patient_id: str = Form(None), file: UploadFile = File(None)):
    if not session_token:
        print("No available session found.")
        return RedirectResponse(url="/")
    
    if request.method == "GET":
        return templates.TemplateResponse("scan-page.html", {"request": request})

    elif request.method == "POST":
        if not file:
            return JSONResponse({"error": "No file uploaded"}, status_code=400)
        print("Patient ID:", patient_id)
        print("Filename:", file.filename)

        # Kök dizine göre statik klasörün altına kaydetmek istiyorsan:
        base_dir = os.path.dirname(__file__)  # current file's directory
        upload_dir = os.path.join(base_dir, "static", "upload")
        os.makedirs(upload_dir, exist_ok=True)  # klasör yoksa oluştur

        current_utc_time_str = datetime.now(timezone.utc).strftime("%d-%m-%Y_%H-%M-%S")
        base_name, extension = os.path.splitext(file.filename)
        image_name = "result_" + patient_id + "_" + current_utc_time_str + extension
        file_location = os.path.join(upload_dir, image_name)
        print(file_location)
        # Dosya içeriğini oku (sadece 1 kez!)
        contents = await file.read()

        with open(file_location, "wb") as f:
            f.write(contents)

        model_path = os.path.join(base_dir, "model.h5")

        model = load_model(model_path)

        class_names = ['glioma_tumor', 'meningioma_tumor', 'no_tumor', 'pituitary_tumor']

        img = Image.open(file_location).convert('RGB')

        img_resized = img.resize((224, 224))

        img_array = image.img_to_array(img_resized)
        img_array = img_array / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        pred_probs = model.predict(img_array)
        pred_index = np.argmax(pred_probs)
        pred_label = class_names[pred_index]
        confidence = pred_probs[0][pred_index]
        print(f"Prediction Rate: {(confidence * 100):.2f}% Prediction Label: {pred_label}")
        if confidence < 0.80:
            return JSONResponse({"message": f"Low accuracy rates, try another mri."})

        pat_ref = db.collection("patient").document(patient_id)
        patient = pat_ref.get()
        
        if not patient.exists:
            return JSONResponse({"error": "Patient not found"}, status_code=404)
            
        patient_data = patient.to_dict()
        
        # Check if patient data has required fields
        age = patient_data.get('age', 'Unknown')
        gender = "Male" if patient_data.get('gender', False) else "Female"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            Create a concise medical report for a brain surgeon (max 200 words).
            
            PATIENT INFORMATION:
            Patient = {patient_data.get('name', 'Unknown')} {patient_data.get('surname', 'Unknown')}
            Height = {patient_data.get('height', 'Unknown')}
            Weight = {patient_data.get('weight', 'Unknown')}
            Age = {age}
            Sex = {'M' if gender == 'Male' else 'F'}
            
            TUMOR REPORT:
            Provide a brief analysis of the detected {pred_label} including:
            - Tumor characteristics
            - Key surgical considerations
            - Immediate recommendations
            
            FORMAT REQUIREMENTS:
            - Put each section on a separate line
            - Add blank lines between sections
            - Do not use markdown or bold formatting
            - Make it look like this:
            
            PATIENT INFORMATION:
            [patient details]
            
            TUMOR ANALYSIS:
            [tumor details]
            
            SURGICAL CONSIDERATIONS:
            [surgical details]
            
            RECOMMENDATIONS:
            [recommendations]
            """,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
            ),
        )
        print(response.text)
        
        # Save the result to the database!
        result_collection = db.collection("results")

        # If the results can be deleted than this aproach is wrong.
        result = {
            "description": response.text,
            "doctor_id": session_token,
            "name": "Result" +"[" + current_utc_time_str + "]",
            "patient_id": patient_id,
            "pred_rate": float(confidence),
            "scanned_on": firestore.SERVER_TIMESTAMP,
            "tumor_type": pred_label.replace("_"," ").title(),
            "image_path": "upload/" + image_name
        }
        result_collection.add(result)
        return JSONResponse({"message": f"Analysis made successfully,\n check the patient results section."})

@app.get("/log-out")
async def log_out(session_token: str = Cookie(None)):
    try:
        if not session_token:
            print("No available session found.")
            return RedirectResponse(url="/")
        
        response = RedirectResponse(url="/")

        response.set_cookie(
            key="session_token",
            value="",
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=0 
        )

        return response
    except Exception as e:
        print("Exception in /logo-ut:")
        traceback.print_exc()
        return RedirectResponse(url="/")

@app.get("/doctor-area")
async def doctor_area(token: str = Query(...)):
    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        doc_ref = db.collection("doctor").document(uid)
        if not doc_ref.get().exists:
            return RedirectResponse(url="/")

        response = RedirectResponse(url="/scan-mri")

        response.set_cookie(
            key="session_token",
            value=uid,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=3600*24 # 1 day
        )
        return response
    except Exception as e:
        print("Exception in /doctor-area:")
        traceback.print_exc()
        return RedirectResponse(url="/")

@app.get("/doctor-info")
async def doctor_info(request: Request, session_token: str = Cookie(None)):
    if not session_token:
        print("No available session found.")
        return RedirectResponse(url="/")
    doc_ref = db.collection("doctor").document(session_token)
    patients = db.collection("patient").stream()
    counter = 0
    for patient in patients:
        patient_data = patient.to_dict()
        if patient_data["doctor"] == session_token:
            counter += 1
    doc = doc_ref.get()

    if not doc.exists:
        return JSONResponse({"error": "Doctor not found"}, status_code=404)

    doctor_data = doc.to_dict()

    created_on = doctor_data.get("created_on")
    # If created_on is DatetimeWithNanoseconds, convert it to datetime
    if isinstance(created_on, DatetimeWithNanoseconds):
        created_on = datetime.fromtimestamp(created_on.timestamp())

    response = {
        "name": doctor_data.get("name"),
        "surname": doctor_data.get("surname"),
        "institution": doctor_data.get("institution"),
        "title": doctor_data.get("title"),
        "created_on": created_on.strftime("%d/%m/%Y"),
        "patient_count": counter
    }

    return {"message": "Fetched doctor response", "data": response}

@app.get("/result/{result_id}")
async def result_info(request: Request, result_id: str, session_token: str = Cookie(None)):
    if not session_token:
        print("No available session found.")
        return RedirectResponse(url="/")
    
    result_ref = db.collection("results").document(result_id)
    res = result_ref.get()

    if not res.exists:
        return JSONResponse({"error": "Doctor not found"}, status_code=404)

    result_data = res.to_dict()
    print(result_data)
    # Take the patient
    pat_ref = db.collection("patient").document(result_data["patient_id"])
    pat = pat_ref.get()
    patient_data = pat.to_dict()

    scanned_on = result_data.get("scanned_on")
    # If created_on is DatetimeWithNanoseconds, convert it to datetime
    if isinstance(scanned_on, DatetimeWithNanoseconds):
        scanned_on = datetime.fromtimestamp(scanned_on.timestamp())

    response = {
        "title": result_data.get("name"),
        "patient_name":  patient_data.get("name") +" "+patient_data.get("surname"),
        "tumor_type": result_data.get("tumor_type"),
        "pred_rate": round(result_data.get("pred_rate")*100, 2),
        "description": result_data.get("description"),
        "image_path": result_data.get("image_path"),
        "scanned_on": scanned_on.strftime("%d/%m/%Y %H:%M:%S")
    }

    return {"message": "Fetched doctor response", "data": response}

@app.get("/patient-profile/{patient_id}", response_class=HTMLResponse)
async def patient_profile(request: Request, patient_id: str, session_token: str = Cookie(None)):
    if not session_token:
        return RedirectResponse(url="/")
    patient_ref = db.collection("patient").document(patient_id)
    patient = patient_ref.get()
    if not patient.exists:
        return JSONResponse({"error": "Patient not found"}, status_code=404)
    patient_data = patient.to_dict()
    patient_data["gender"] = "Male" if patient_data["gender"] else "Female"
    all_results = db.collection("results").stream()
    results = []
    counter = 0
    for result_doc in all_results:
        result_data = result_doc.to_dict()
        if result_data["patient_id"] != patient_id:
            continue
        scanned_on = result_data.get("scanned_on")
        if isinstance(scanned_on, DatetimeWithNanoseconds):
            scanned_on = datetime.fromtimestamp(scanned_on.timestamp())
        if patient_id == result_data["patient_id"]:
            counter += 1

        results.append({
            "id": result_doc.id,
            "name": result_data["name"],
            "tumor_type": result_data["tumor_type"],
            "scanned_on": scanned_on.strftime("%d/%m/%Y %H:%M:%S") if scanned_on else None
        })
    patient_data["total_scans"] = counter
    results.sort(key=lambda r: r["scanned_on"], reverse=True)
    for i in range(0, len(results)):
        results[i]["order"] = i + 1

    return templates.TemplateResponse("patient-profile.html", {"request": request, "patient": patient_data, "results": results})

@app.post("/create-patient")
async def create_patient(
    name: str = Form(...),
    surname: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    age: int = Form(...),
    gender: str = Form(...),  
    session_token: str = Cookie(None)
):
    if not session_token:
        return RedirectResponse(url="/")
    try:
        # Gender string'ini bool'a çevir: True=Male, False=Female
        gender_bool = True if gender.lower() == "male" else False
        
        patient_data = {
            "name": name,
            "surname": surname,
            "height": height,
            "weight": weight,
            "age": age,
            "gender": gender_bool,
            "doctor": session_token
        }
        db.collection("patient").add(patient_data)
        return {"message": "Hasta başarıyla eklendi."}
    except Exception as e:
        print("Hasta eklerken hata:", e)
        return JSONResponse({"error": "Hasta eklenemedi."}, status_code=500)

@app.put("/edit-patient/{patient_id}")
async def edit_patient(
    patient_id: str,
    name: str = Form(...),
    surname: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    session_token: str = Cookie(None)
):
    if not session_token:
        return RedirectResponse(url="/")
    try:
        patient_ref = db.collection("patient").document(patient_id)
        patient = patient_ref.get()
        if not patient.exists:
            return JSONResponse({"error": "Hasta bulunamadı."}, status_code=404)
        if patient.to_dict().get("doctor") != session_token:
            return JSONResponse({"error": "Bu hastayı düzenleme yetkiniz yok."}, status_code=403)
        
        # Gender string'ini bool'a çevir: True=Male, False=Female
        gender_bool = True if gender.lower() == "male" else False
        
        updated_data = {
            "name": name,
            "surname": surname,
            "height": height,
            "weight": weight,
            "age": age,
            "gender": gender_bool
        }
        patient_ref.update(updated_data)
        return {"message": "Hasta başarıyla güncellendi."}
    except Exception as e:
        print("Hasta güncellerken hata:", e)
        return JSONResponse({"error": "Hasta güncellenemedi."}, status_code=500)

@app.delete("/delete-patient/{patient_id}")
async def delete_patient(patient_id: str, session_token: str = Cookie(None)):
    if not session_token:
        return RedirectResponse(url="/")
    try:
        patient_ref = db.collection("patient").document(patient_id)
        patient = patient_ref.get()
        if not patient.exists:
            return JSONResponse({"error": "Hasta bulunamadı."}, status_code=404)
        if patient.to_dict().get("doctor") != session_token:
            return JSONResponse({"error": "Bu hastayı silme yetkiniz yok."}, status_code=403)
        patient_ref.delete()
        return {"message": "Hasta başarıyla silindi."}
    except Exception as e:
        print("Hasta silerken hata:", e)
        return JSONResponse({"error": "Hasta silinemedi."}, status_code=500)
    
@app.post("/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    session_token: str = Cookie(None)
):
    """
    Handles requests to change a user's password.
    Requires the current password, new password, and a session token.
    """
    
    if not session_token:
        print("No available session found.")
      
        return RedirectResponse(url="/")
    
    try:
        uid = session_token
        try:
           
            user = auth.get_user(uid)
            user_email = user.email
        except Exception as e:
            print("User not found:", e)
            return JSONResponse({"error": "User not found."}, status_code=404)
        
       
        print(f"Verifying password for user: {user_email}")
       
        password_verified = verify_firebase_password(user_email, current_password)
        print(f"Password verification result: {password_verified}")
        if not password_verified:
            return JSONResponse({"error": "Incorrect current password."}, status_code=400)
        
        if len(new_password) < 6:
            return JSONResponse({"error": "New password must be at least 6 characters long."}, status_code=400)
        
   
        auth.update_user(
            uid=uid,
            password=new_password
        )
        
    
        return JSONResponse({"message": "Password updated successfully."})
        
    except Exception as e:
        print("Exception in /change-password:", e)
        import traceback
        traceback.print_exc() 
        return JSONResponse({"error": "Failed to update password."}, status_code=500)    
    
@app.post("/delete-account")
async def delete_account(
    current_password: str = Form(...),
    session_token: str = Cookie(None)
):
    """
    Deletes the doctor's account and all associated patient and scan data.
    Requires the current password for verification.
    """
    if not session_token:
        print("No available session found for account deletion.")
        return RedirectResponse(url="/")

    try:
        uid = session_token
        try:
            user = auth.get_user(uid)
            user_email = user.email
        except Exception as e:
            print(f"User not found for deletion: {e}")
            return JSONResponse({"error": "User not found."}, status_code=404)

        # Verify current password before proceeding with deletion
        password_verified = verify_firebase_password(user_email, current_password)
        if not password_verified:
            return JSONResponse({"error": "Incorrect current password. Account deletion failed."}, status_code=401)

        # 1. Delete all results associated with the doctor's patients
        patients_ref = db.collection("patient").where("doctor", "==", uid).stream()
        patient_ids_to_delete = []
        for patient_doc in patients_ref:
            patient_ids_to_delete.append(patient_doc.id)
            results_ref = db.collection("results").where("patient_id", "==", patient_doc.id).stream()
            for result_doc in results_ref:
                db.collection("results").document(result_doc.id).delete()
            print(f"Deleted results for patient: {patient_doc.id}")

        # 2. Delete all patients associated with the doctor
        for patient_id in patient_ids_to_delete:
            db.collection("patient").document(patient_id).delete()
        print(f"Deleted {len(patient_ids_to_delete)} patients for doctor: {uid}")

        # 3. Delete the doctor's document from Firestore
        db.collection("doctor").document(uid).delete()
        print(f"Deleted doctor document: {uid}")

        # 4. Delete the user from Firebase Authentication
        auth.delete_user(uid)
        print(f"Deleted Firebase Auth user: {uid}")

        # Clear session cookie
        response = JSONResponse({"message": "Account and all associated data deleted successfully."})
        response.set_cookie(
            key="session_token",
            value="",
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=0 
        )
        return response

    except Exception as e:
        print("Exception in /delete-account:", e)
        traceback.print_exc()
        return JSONResponse({"error": "Failed to delete account."}, status_code=500)    

