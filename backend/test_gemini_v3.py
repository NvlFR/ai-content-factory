import os
from google import genai

def test_simple_list():
    key = os.environ.get("GOOGLE_API_KEY")
    print(f"🔑 Key Check: {key[:5]}..." if key else "❌ Key Missing")
    
    try:
        client = genai.Client(api_key=key)
        print("\n📋 DAFTAR MODEL (Raw List):")
        print("-" * 30)
        
        # Iterasi langsung tanpa filter atribut yang aneh-aneh
        for m in client.models.list():
            # Cukup print namanya saja
            print(f"👉 {m.name}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_simple_list()