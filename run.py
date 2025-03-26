# run.py
from app import create_app, db, socketio

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use socketio.run instead of app.run to enable WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)