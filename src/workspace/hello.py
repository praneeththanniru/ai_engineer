from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/hello', methods=['GET'])
def hello():
    return jsonify({"message":"Hello from Antigravity Agent"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=64306)


from flask import render_template
@app.route('/')
def index():
    return render_template('index.html')
