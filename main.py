import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Read port from environment (defaulting to 8000)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
