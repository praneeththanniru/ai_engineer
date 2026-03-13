from . import db

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')

    def __repr__(self):
        return f"<Task {self.name}>"
