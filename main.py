from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import threading
import time

app = Flask(__name__)

# Session state
session_lock = threading.Lock()
session_thread = None
stop_flag = False
current_number = None

def run_browser(number):
    global stop_flag, session_thread, current_number

    # Setup Chrome
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.thecallbomber.in")

        # Fill form
        driver.find_element(By.ID, "mobileNumber").send_keys(number)
        driver.find_element(By.ID, "terms").click()
        time.sleep(40)
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(3)
        driver.execute_script("window.scrollBy(0, -500);")
        time.sleep(3)
        driver.execute_script("window.scrollBy(0, 100);")
        time.sleep(3)
        driver.find_element(By.ID, "submit").click()
        time.sleep(45)

        # Stop if cancelled
        if stop_flag:
            driver.quit()
            return

        driver.find_element(By.ID, "verify_button").click()
        time.sleep(5)

        # Get new URL
        new_url = driver.current_url
        print(f"🔗 New redirected URL: {new_url}")

        # Open new tabs
        max_tabs = 5  # Adjust based on what Render can hold
        for _ in range(max_tabs):
            driver.execute_script(f"window.open('{new_url}');")
            time.sleep(1)

        # Long wait
        for _ in range(24 * 60 * 60):  # 24 hours in seconds
            if stop_flag:
                print("❌ Session stopped early.")
                break
            time.sleep(1)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
        with session_lock:
            stop_flag = False
            session_thread = None
            current_number = None

@app.route("/start")
def start():
    global session_thread, stop_flag, current_number

    number = request.args.get("number")
    if not number:
        return jsonify({"error": "Number is required"}), 400

    with session_lock:
        # Stop existing session
        if session_thread and session_thread.is_alive():
            print("⚠️ Stopping previous session...")
            stop_flag = True
            session_thread.join(timeout=5)

        # Start new session
        stop_flag = False
        current_number = number
        session_thread = threading.Thread(target=run_browser, args=(number,))
        session_thread.start()

    return jsonify({"status": "Started", "number": number})

@app.route("/status")
def status():
    return jsonify({
        "active_session": session_thread.is_alive() if session_thread else False,
        "number": current_number,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
