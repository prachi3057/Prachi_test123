from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from database import init_db, get_db
from export import export_record_pdf, export_summary_pdf

app = Flask(__name__)
app.secret_key = "medvault_secret_key_2024"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Initialize DB on startup
init_db()
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    patient = db.execute("SELECT * FROM Patient LIMIT 1").fetchone()
    records = db.execute("""
        SELECT Record.*, Category.name as cat_name
        FROM Record
        JOIN Category ON Record.category_id = Category.id
        ORDER BY Record.upload_date DESC LIMIT 5
    """).fetchall()

    # Category counts
    cat_counts = {}
    rows = db.execute("""
        SELECT Category.name, COUNT(Record.id) as cnt
        FROM Category
        LEFT JOIN Record ON Record.category_id = Category.id
        GROUP BY Category.id
    """).fetchall()
    for row in rows:
        cat_counts[row['name']] = row['cnt']

    # Health summary counts
    pid = patient['id'] if patient else None
    meds = db.execute("SELECT * FROM CurrentMedicine WHERE patient_id=?", (pid,)).fetchall() if pid else []
    diseases = db.execute("SELECT * FROM PastDisease WHERE patient_id=?", (pid,)).fetchall() if pid else []
    allergies = db.execute("SELECT * FROM Allergy WHERE patient_id=?", (pid,)).fetchall() if pid else []

    db.close()
    return render_template('index.html',
                           patient=patient,
                           records=records,
                           cat_counts=cat_counts,
                           meds=meds,
                           diseases=diseases,
                           allergies=allergies,
                           total_records=len(records))


# ─────────────────────────────────────────────
# PATIENT PROFILE
# ─────────────────────────────────────────────
@app.route('/patient', methods=['GET', 'POST'])
def patient():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()

        if not name:
            flash('Name is required.', 'error')
            return redirect(url_for('patient'))

        existing = db.execute("SELECT id FROM Patient LIMIT 1").fetchone()
        if existing:
            db.execute("""
                UPDATE Patient SET name=?, age=?, gender=?, blood_group=?, emergency_contact=?
                WHERE id=?
            """, (name, age, gender, blood_group, emergency_contact, existing['id']))
        else:
            db.execute("""
                INSERT INTO Patient(name, age, gender, blood_group, emergency_contact)
                VALUES(?, ?, ?, ?, ?)
            """, (name, age, gender, blood_group, emergency_contact))
        db.commit()
        flash('Profile saved successfully!', 'success')
        db.close()
        return redirect(url_for('patient'))

    patient = db.execute("SELECT * FROM Patient LIMIT 1").fetchone()
    db.close()
    return render_template('patient.html', patient=patient)


# ─────────────────────────────────────────────
# RECORDS
# ─────────────────────────────────────────────
@app.route('/records', methods=['GET', 'POST'])
def records():
    db = get_db()

    if request.method == 'POST':
        patient = db.execute("SELECT id FROM Patient LIMIT 1").fetchone()
        if not patient:
            flash('Please set up your patient profile first.', 'error')
            db.close()
            return redirect(url_for('patient'))

        file = request.files.get('file')
        file_name = request.form.get('file_name', '').strip()
        category_id = request.form.get('category_id', '1')

        if not file or file.filename == '':
            flash('Please select a file to upload.', 'error')
        elif not allowed_file(file.filename):
            flash('Only PDF, PNG, JPG files are allowed.', 'error')
        elif not file_name:
            flash('Please enter a record name.', 'error')
        else:
            filename = secure_filename(file.filename)
            # Make filename unique
            base, ext = os.path.splitext(filename)
            import time
            unique_filename = f"{base}_{int(time.time())}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(save_path)

            db.execute("""
                INSERT INTO Record(patient_id, category_id, file_name, file_path, file_type)
                VALUES(?, ?, ?, ?, ?)
            """, (patient['id'], category_id, file_name, unique_filename,
                  file.content_type or ext.lstrip('.')))
            db.commit()
            flash('Record uploaded successfully!', 'success')

        db.close()
        return redirect(url_for('records'))

    # GET — show records with optional category filter
    cat_filter = request.args.get('cat', 'all')
    categories = db.execute("SELECT * FROM Category").fetchall()

    if cat_filter == 'all':
        all_records = db.execute("""
            SELECT Record.*, Category.name as cat_name
            FROM Record JOIN Category ON Record.category_id = Category.id
            ORDER BY Record.upload_date DESC
        """).fetchall()
    else:
        all_records = db.execute("""
            SELECT Record.*, Category.name as cat_name
            FROM Record JOIN Category ON Record.category_id = Category.id
            WHERE Category.name = ?
            ORDER BY Record.upload_date DESC
        """, (cat_filter,)).fetchall()

    db.close()
    return render_template('records.html',
                           records=all_records,
                           categories=categories,
                           cat_filter=cat_filter)


@app.route('/records/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    db = get_db()
    record = db.execute("SELECT file_path FROM Record WHERE id=?", (record_id,)).fetchone()
    if record:
        # Delete actual file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], record['file_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
        db.execute("DELETE FROM Record WHERE id=?", (record_id,))
        db.commit()
        flash('Record deleted.', 'success')
    db.close()
    return redirect(url_for('records'))


@app.route('/records/export/<int:record_id>')
def export_record(record_id):
    db = get_db()
    record = db.execute("""
        SELECT Record.*, Category.name as cat_name
        FROM Record JOIN Category ON Record.category_id = Category.id
        WHERE Record.id=?
    """, (record_id,)).fetchone()
    patient = db.execute("SELECT * FROM Patient LIMIT 1").fetchone()
    db.close()

    if not record:
        flash('Record not found.', 'error')
        return redirect(url_for('records'))

    pdf_path = export_record_pdf(record, patient)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{record['file_name']}.pdf")


# ─────────────────────────────────────────────
# HEALTH SUMMARY
# ─────────────────────────────────────────────
@app.route('/health', methods=['GET', 'POST'])
def health():
    db = get_db()
    patient = db.execute("SELECT * FROM Patient LIMIT 1").fetchone()
    pid = patient['id'] if patient else None

    if request.method == 'POST' and pid:
        action = request.form.get('action')

        if action == 'add_medicine':
            text = request.form.get('medicine_text', '').strip()
            if text:
                db.execute("INSERT INTO CurrentMedicine(patient_id, medicine_text) VALUES(?,?)", (pid, text))
                db.commit()
                flash('Medicine added.', 'success')

        elif action == 'delete_medicine':
            med_id = request.form.get('item_id')
            db.execute("DELETE FROM CurrentMedicine WHERE id=? AND patient_id=?", (med_id, pid))
            db.commit()

        elif action == 'add_disease':
            name = request.form.get('disease_name', '').strip()
            if name:
                db.execute("INSERT INTO PastDisease(patient_id, disease_name) VALUES(?,?)", (pid, name))
                db.commit()
                flash('Disease added.', 'success')

        elif action == 'delete_disease':
            dis_id = request.form.get('item_id')
            db.execute("DELETE FROM PastDisease WHERE id=? AND patient_id=?", (dis_id, pid))
            db.commit()

        elif action == 'add_allergy':
            name = request.form.get('allergy_name', '').strip()
            if name:
                db.execute("INSERT INTO Allergy(patient_id, allergy_name) VALUES(?,?)", (pid, name))
                db.commit()
                flash('Allergy added.', 'success')

        elif action == 'delete_allergy':
            al_id = request.form.get('item_id')
            db.execute("DELETE FROM Allergy WHERE id=? AND patient_id=?", (al_id, pid))
            db.commit()

        db.close()
        return redirect(url_for('health'))

    medicines = db.execute("SELECT * FROM CurrentMedicine WHERE patient_id=?", (pid,)).fetchall() if pid else []
    diseases = db.execute("SELECT * FROM PastDisease WHERE patient_id=?", (pid,)).fetchall() if pid else []
    allergies = db.execute("SELECT * FROM Allergy WHERE patient_id=?", (pid,)).fetchall() if pid else []
    db.close()

    return render_template('health_summary.html',
                           patient=patient,
                           medicines=medicines,
                           diseases=diseases,
                           allergies=allergies)


@app.route('/health/export')
def export_summary():
    db = get_db()
    patient = db.execute("SELECT * FROM Patient LIMIT 1").fetchone()
    pid = patient['id'] if patient else None
    medicines = db.execute("SELECT * FROM CurrentMedicine WHERE patient_id=?", (pid,)).fetchall() if pid else []
    diseases = db.execute("SELECT * FROM PastDisease WHERE patient_id=?", (pid,)).fetchall() if pid else []
    allergies = db.execute("SELECT * FROM Allergy WHERE patient_id=?", (pid,)).fetchall() if pid else []
    recent = db.execute("""
        SELECT Record.file_name, Category.name as cat_name, Record.upload_date
        FROM Record JOIN Category ON Record.category_id = Category.id
        WHERE Record.patient_id=?
        ORDER BY Record.upload_date DESC LIMIT 5
    """, (pid,)).fetchall() if pid else []
    db.close()

    pdf_path = export_summary_pdf(patient, medicines, diseases, allergies, recent)
    return send_file(pdf_path, as_attachment=True, download_name="health_summary.pdf")

# ───────────── AI (FAKE - NO API NEEDED) ─────────────
from flask import jsonify
import time

@app.route('/ai-health', methods=['POST'])
def ai_health():
    data = request.get_json()
    prompt = data.get("prompt", "").lower()

    time.sleep(1)

    result = """**Health Overview:** Your condition looks stable.

**Tips:** Eat healthy, stay hydrated, and exercise regularly.

**Advice:** Regular checkups are recommended.

**Positive Note:** You are managing your health well!"""

    return jsonify({"result": result})


@app.route('/ai-summary', methods=['POST'])
def ai_summary():
    data = request.get_json()

    time.sleep(1)

    result = """**Record Summary:** This record contains important medical details.

**Advice:** Review carefully and consult your doctor.

**Tip:** Keep all reports organized."""

    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
