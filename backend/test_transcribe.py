import os
from openai import OpenAI

# Setup Client OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

VIDEO_PATH = "downloads/jNQXAC9IVRw.mp4"

def transcribe_video():
    print(f"🎧 Membaca file audio dari: {VIDEO_PATH}")
    
    if not os.path.exists(VIDEO_PATH):
        print("❌ File video tidak ditemukan! Jalankan test_download.py dulu.")
        return

    try:
        with open(VIDEO_PATH, "rb") as audio_file:
            print("⏳ Mengirim ke OpenAI Whisper (Mohon tunggu)...")
            
            # Panggil API Whisper (Revisi: Hapus timestamp_granularities)
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="verbose_json" # Ini sudah cukup untuk dapat timestamp
            )

            print("\n✅ Transkripsi Sukses!")
            print("="*50)
            print(f"📜 Full Text: {transcript.text}")
            print("="*50)
            
            # Tampilkan segmen dengan timestamp
            print("\n⏱️ Segmen Waktu:")
            # Karena strukturnya bisa berupa object atau dict, kita handle dua-duanya
            segments = getattr(transcript, 'segments', []) or []
            
            for segment in segments:
                # Akses data segmen dengan aman
                start = segment['start'] if isinstance(segment, dict) else segment.start
                end = segment['end'] if isinstance(segment, dict) else segment.end
                text = segment['text'] if isinstance(segment, dict) else segment.text
                
                print(f"[{start:.2f}s - {end:.2f}s] -> {text}")
            
            return transcript

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    transcribe_video()