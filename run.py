from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("SettleUp is running at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)