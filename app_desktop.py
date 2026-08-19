import webview
import threading
from server import run  # your existing Flask server runner

def start_server():
    # Run your Flask server in a background thread
    run(open_browser=False)  # we'll open the webview ourselves

if __name__ == '__main__':
    # Start the Flask server in a daemon thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # Create a native window that points to the local server
    webview.create_window(
        'Finance Logger',
        'http://127.0.0.1:5000',  # your server URL
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()
