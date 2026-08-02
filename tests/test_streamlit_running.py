import requests
import time

def test_streamlit():
    try:
        response = requests.get("http://localhost:8501")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Streamlit is responding.")
        else:
            print("Streamlit returned an error.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_streamlit()
