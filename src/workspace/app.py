from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
login_manager = LoginManager()
login_manager.init_app(app)
USERS = {}

class User(UserMixin):
    def __init__(self, id, password):
        self.id = id
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return USERS.get(user_id)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    id = data.get('username')
    password = data.get('password')
    if not id or not password:
        return jsonify({'message': 'Missing username or password'}), 400
    USERS[id] = User(id, password)
    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    id = data.get('username')
    password = data.get('password')
    user = USERS.get(id)
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid credentials'}), 401
    login_user(user, remember=True)
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = serializer.dumps(id)
    return jsonify({'message': 'Logged in successfully', 'token': token}), 200

@app.route('/hello', methods=['GET'])
@login_required
def hello():
    return jsonify({"message": f"Hello {current_user.id} from Antigravity Agent"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)