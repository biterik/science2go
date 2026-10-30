#!/usr/bin/env python
"""
check_voices.py - verify that Science2Go can reach Google Cloud Text-to-Speech
and that every voice offered in the GUI is still available.

Run from this folder with the science2go environment's Python:
    ~/miniforge3/envs/science2go/bin/python check_voices.py

It (1) reports which credentials are found, (2) lists the en-GB voices Google
offers and compares them with the voices in src/processors/audio_generator.py,
(3) synthesises one short sentence with the default voice into
output/voice_check.mp3 (costs a fraction of a cent), and (4) checks the
Gemini key used for the text-cleanup step.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# make the environment's own tools (ffmpeg) findable, as run.sh does
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
sys.path.insert(0, str(HERE))

ok = True
print("== 1. Credentials ==")
gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
adc = Path.home() / ".config/gcloud/application_default_credentials.json"
api_key = os.environ.get("GOOGLE_API_KEY", "")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {gac or '(not set)'}"
      + ("" if not gac else ("  [file exists]" if Path(gac).exists() else "  [FILE MISSING]")))
print(f"  gcloud login file (ADC): {'found' if adc.exists() else 'not found'} ({adc})")
print(f"  GOOGLE_API_KEY: {'set' if api_key else 'not set'}")
print(f"  GEMINI_API_KEY: {'set' if os.environ.get('GEMINI_API_KEY') else 'not set'}")

try:
    from google.cloud import texttospeech
except ImportError:
    sys.exit("  ERROR: google-cloud-texttospeech not installed -> wrong Python/environment?")

import importlib
# import the module itself (src.processors also exports an object of the same name)
ag = importlib.import_module("src.processors.audio_generator")

if gac and Path(gac).exists():
    client = texttospeech.TextToSpeechClient()
elif adc.exists():
    client = texttospeech.TextToSpeechClient()
elif api_key:
    client = texttospeech.TextToSpeechClient(client_options={"api_key": api_key})
else:
    sys.exit("  ERROR: no Google Cloud TTS credentials found (see recipe).")

print("\n== 2. Voices ==")
try:
    voices = client.list_voices(language_code="en-GB").voices
except Exception as e:
    sys.exit(f"  ERROR: could not list voices: {e}")
available = {v.name for v in voices}
wanted = ag.ALL_CHIRP3_HD_VOICES + ag.ALL_NEURAL2_VOICES
missing = [v for v in wanted if v not in available]
print(f"  Google offers {len(available)} en-GB voices; Science2Go uses {len(wanted)}.")
if missing:
    ok = False
    print(f"  MISSING ({len(missing)}): {', '.join(missing)}")
else:
    print("  All Science2Go voices are available.")
new_chirp = sorted(v for v in available if "Chirp3-HD" in v and v not in wanted)
if new_chirp:
    print(f"  New Chirp 3 HD voices not yet in the GUI: {', '.join(new_chirp)}")

print(f"\n== 3. Test synthesis with {ag.DEFAULT_VOICE} ==")
try:
    resp = client.synthesize_speech(
        input=texttospeech.SynthesisInput(
            text="Welcome to Science to Go. This is a short voice check."),
        voice=texttospeech.VoiceSelectionParams(
            language_code="en-GB", name=ag.DEFAULT_VOICE),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=ag.DEFAULT_SPEAKING_RATE))
    out = HERE / "output" / "voice_check.mp3"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(resp.audio_content)
    print(f"  OK: wrote {out} ({len(resp.audio_content)//1024} kB)")
    if sys.platform == "darwin":  # play it on the Mac's speakers
        import subprocess
        print("  Playing it now (about 3 seconds)...")
        subprocess.run(["afplay", str(out)], check=False)
except Exception as e:
    ok = False
    print(f"  ERROR: synthesis failed: {e}")

print("\n== 4. Gemini (text cleanup) ==")
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except ImportError:
    pass
vproj = os.environ.get("SCIENCE2GO_VERTEX_PROJECT")
key = os.environ.get("GEMINI_API_KEY")
try:
    from google import genai
    model = os.environ.get("SCIENCE2GO_GEMINI_MODEL", "gemini-2.5-flash")
    if vproj:
        loc = os.environ.get("SCIENCE2GO_VERTEX_LOCATION", "eu")
        tries = [loc] + (["global"] if loc != "global" else [])
    elif key:
        tries = [None]
    else:
        raise RuntimeError("neither SCIENCE2GO_VERTEX_PROJECT nor GEMINI_API_KEY set")
    for i, loc in enumerate(tries):
        if loc:
            print(f"  Route: Vertex AI, project {vproj}, region {loc}, model {model}")
            client = genai.Client(vertexai=True, project=vproj, location=loc)
        else:
            print(f"  Route: Gemini API key (AI Studio), model {model}")
            client = genai.Client(api_key=key)
        try:
            reply = client.models.generate_content(
                model=model, contents="Reply with the single word: ready")
            print(f"  OK: test call answered: {(reply.text or '').strip()[:40]!r}")
            if i > 0:
                print(f"  NOTE: worked only in region '{loc}' -> set "
                      f"SCIENCE2GO_VERTEX_LOCATION={loc} in .env")
            break
        except Exception as e:
            if i == len(tries) - 1:
                raise
            print(f"  failed in region '{loc}': {str(e)[:160]}")
except Exception as e:
    ok = False
    print(f"  ERROR: {e}")

print("\nRESULT:", "ALL GOOD" if ok else "PROBLEMS FOUND (see above)")
