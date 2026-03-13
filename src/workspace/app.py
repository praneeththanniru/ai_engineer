from flask import Flask, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the Flask application
app = Flask(__name__)
# Set a secret key for session management
app.config['SECRET_KEY'] = 'secret'
# Initialize the LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
# Dictionary to store user data
USERS = {}

# Define a User class inheriting from UserMixin
class User(UserMixin):
    def __init__(self, id, password):
        self.id = id
        # Hash the password for security
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        # Check if the provided password matches the stored hash
        return check_password_hash(self.password_hash, password)

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return USERS.get(user_id)

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    id = data.get('username')
    password = data.get('password')
    if not id or not password:
        return jsonify({'message': 'Missing username or password'}), 400
    # Create a new user and store it in the USERS dictionary
    USERS[id] = User(id, password)
    return jsonify({'message': 'Registration successful'}), 201

# Route for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    id = data.get('username')
    password = data.get('password')
    user = USERS.get(id)
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid credentials'}), 401
    # Log the user in
    login_user(user, remember=True)
    return jsonify({'message': 'Logged in successfully'}), 200

# Protected route that requires login
@app.route('/hello', methods=['GET'])
@login_required
def hello():
    return jsonify({"message": "Hello from Antigravity Agent"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)