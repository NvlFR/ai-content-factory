import json

# Ini data "Palsu" yang meniru format jawaban asli OpenAI Whisper
# Video: "Me at the zoo" (19 detik)
MOCK_RESPONSE = {
    "text": "All right, so here we are in front of the elephants. The cool thing about these guys is that they have really, really, really long trunks, and that's, that's cool. And that's pretty much all there is to say.",
    "segments": [
        {
            "id": 0,
            "start": 0.0,
            "end": 4.5,
            "text": "All right, so here we are in front of the elephants."
        },
        {
            "id": 1,
            "start": 4.5,
            "end": 9.5,
            "text": "The cool thing about these guys is that they have really, really, really long trunks,"
        },
        {
            "id": 2,
            "start": 9.5,
            "end": 11.5,
            "text": "and that's, that's cool."
        },
        {
            "id": 3,
            "start": 11.5,
            "end": 19.0,
            "text": "And that's pretty much all there is to say."
        }
    ]
}

def transcribe_video_mock():
    print(f"🎧 [MOCK MODE] Membaca file audio dari: downloads/jNQXAC9IVRw.mp4")
    print("⏳ Mengirim ke OpenAI Whisper (Pura-pura)...")
    
    # Kita langsung return data palsu tanpa panggil API
    transcript = MOCK_RESPONSE
    
    print("\n✅ Transkripsi Sukses! (Data Mock)")
    print("="*50)
    print(f"📜 Full Text: {transcript['text']}")
    print("="*50)
    
    print("\n⏱️ Segmen Waktu:")
    for segment in transcript['segments']:
        print(f"[{segment['start']}s - {segment['end']}s] -> {segment['text']}")
        
    # Simpan hasil ke JSON file agar bisa dipakai tahap selanjutnya
    with open("downloads/transcript.json", "w") as f:
        json.dump(transcript, f, indent=2)
        print("\n💾 Data transkrip disimpan ke 'downloads/transcript.json'")

if __name__ == "__main__":
    transcribe_video_mock()