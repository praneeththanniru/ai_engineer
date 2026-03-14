from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/world', methods=['GET'])
def world():
    return jsonify({"message":"Hello from Antigravity Agent"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=55344)
