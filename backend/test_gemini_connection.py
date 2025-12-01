import os
from google import genai

def test_connection():
    print("🕵️‍♂️  MEMERIKSA KONEKSI GEMINI...")
    print("-" * 30)

    # 1. Cek Variable Environment
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ CRITICAL ERROR: Environment variable 'GEMINI_API_KEY' Kosong/None!")
        print("   Artinya Docker tidak berhasil membaca file .env Anda.")
        return

    # Tampilkan 4 huruf depan saja (demi keamanan) untuk memastikan isinya benar
    masked_key = f"{api_key[:4]}...{api_key[-4:]}"
    print(f"✅ API Key Terdeteksi: {masked_key}")

    # 2. Cek Koneksi ke Google
    print("⏳ Mengontak Server Google AI...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content("Hello Gemini, are you online? Reply with 'Yes, I am ready!'")
        
        print(f"✅ Balasan Gemini: {response.text}")
        print("-" * 30)
        print("🎉 KESIMPULAN: Koneksi Sukses! Masalah ada di pipeline.py (mungkin salah import/config).")
        
    except Exception as e:
        print(f"❌ Koneksi Gagal: {str(e)}")
        print("-" * 30)
        print("KESIMPULAN: Key ada, tapi ditolak Google (Salah copy atau kuota habis).")

if __name__ == "__main__":
    test_connection()