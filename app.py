from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
from models import db, User, Document, ChatHistory
from rag import RAGSystem
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize RAG system
rag_system = RAGSystem()

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('vector_store', exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
            
        user = User(
            username=username,
            password=generate_password_hash(password),
            email=email,
            role=role
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    users = User.query.all() if current_user.role == 'admin' else []
    documents = Document.query.all() if current_user.role == 'admin' else Document.query.filter_by(user_id=current_user.id).all()
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', 
                         user=current_user,
                         users=users,
                         documents=documents,
                         chat_history=chat_history)

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        message = request.json.get('message')
        
        # Get relevant documents from RAG
        relevant_docs = rag_system.query(message)
        
        # Prepare context from relevant documents
        context = "\n".join([doc['content'] for doc in relevant_docs])
        
        # Call Ollama API
        response = requests.post('http://localhost:11434/api/generate',
                               json={
                                   'model': 'gemma3:1b',
                                   'prompt': f"""You are SRM AP University's official AI assistant. \
Your role is to provide accurate, helpful, and courteous information to students, faculty, staff, and visitors. \
Always respond as a knowledgeable and professional representative of SRM AP University. \
Use only the provided context to answer questions related to academics, admissions, campus facilities, events, policies, and university life. \
If a question is outside your knowledge or the provided context, politely inform the user that you do not have that information and suggest contacting the appropriate university office or visiting the official website.\n\nContext: {context}\n\nQuestion: {message}\n\nAnswer:""",
                                   'stream': False
                               })
        
        if response.status_code == 200:
            ai_response = response.json()['response']
            
            # Save chat history
            chat = ChatHistory(
                user_id=current_user.id,
                message=message,
                response=ai_response,
                used_documents=json.dumps([doc['id'] for doc in relevant_docs])
            )
            db.session.add(chat)
            db.session.commit()
            
            return jsonify({'response': ai_response})
            
        else:
            print(f"Ollama API error: Status Code - {response.status_code}, Response Text - {response.text}")
            return jsonify({'error': f"Error from Ollama API: Status Code {response.status_code}"}), response.status_code

    return render_template('chat.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role not in ['admin', 'faculty']:
        flash('Only faculty and admin can upload documents')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Process document with RAG
            doc = Document(
                title=request.form.get('title', filename),
                filename=filename,
                file_type=filename.split('.')[-1],
                user_id=current_user.id
            )
            db.session.add(doc)
            db.session.commit()
            
            rag_system.process_document(file_path, doc.id)
            doc.is_processed = True
            db.session.commit()
            
            flash('Document uploaded and processed successfully')
            return redirect(url_for('dashboard'))
    
    # Get user's documents
    documents = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('upload.html', documents=documents)

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))
        
    users = User.query.all()
    documents = Document.query.all()
    return render_template('admin.html', users=users, documents=documents)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 