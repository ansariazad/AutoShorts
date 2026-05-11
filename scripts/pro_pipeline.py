#!/usr/bin/env python3
"""
AutoShorts PRO Pipeline — God-Level Edition.
Produces a video from topic → AI script → validation → voice → footage → assembly → upload.

Usage:
  python3 scripts/pro_pipeline.py "crosses their arms when you speak"
  python3 scripts/pro_pipeline.py                    # Random proven topic
  python3 scripts/pro_pipeline.py --ai                # AI-generated topic from trends
  python3 scripts/pro_pipeline.py --dry-run            # Test without uploading
  python3 scripts/pro_pipeline.py --from-manifest '{}'  # From n8n workflow
  python3 scripts/pro_pipeline.py --niche data_storytelling --ai  # Different niche

God-Level Pipeline:
  1. AI generates script using SAECS framework (or use proven topics)
  2. Validation AI scores the script (hook, accuracy, boredom, loop, CTA)
  3. REJECT → retry with feedback (up to 3 attempts)
  4. APPROVE → voice → footage → assembly → upload (unlisted→public)
  5. Fallback to PROVEN_TOPICS if AI fails all retries
"""

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import time
import yaml
import requests
from pathlib import Path
from datetime import datetime, timedelta

# ── Setup ──
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

from god_level_prompts import GodLevelPrompts
from topic_tracker import TopicTracker
from content_variety import ContentVariety

PROVEN_TOPICS = [
    {
        "topic": "copies how you sit",
        "script": "If someone copies how you sit, they're not mocking you. They're mirroring you. Their subconscious trusts you. But if they do it on purpose, they want something from you. Follow for more.",
        "search": ["person sitting dark room", "people sitting together dark", "mirror reflection dark"],
        "pin": "Tag someone who copies everything you do 👀"
    },
    {
        "topic": "stares at you then looks away fast",
        "script": "If someone stares at you then looks away fast, they're not shy. They got caught studying you. Their brain was collecting data. You weren't supposed to notice. Follow for more.",
        "search": ["person staring dark", "eyes looking away dark", "person watching dark room"],
        "pin": "Be honest… who does this to you? 👀"
    },
    {
        "topic": "texts back in one word",
        "script": "If someone texts you back with one word, they're not busy. They're telling you where you stand. One word is not a reply. It's a wall. Follow for more.",
        "search": ["person texting phone dark", "phone screen dark room", "person alone phone dark"],
        "pin": "K. 😂 Tag someone who does this"
    },
    {
        "topic": "yawns right after you start talking",
        "script": "If someone yawns right after you start talking, they're not tired. Their brain is rejecting what you're saying. The yawn is an escape response. Your words triggered shutdown. Follow for more.",
        "search": ["person yawning dark", "tired person dark room", "bored face dark"],
        "pin": "Did someone just yawn reading this? 😂"
    },
    {
        "topic": "keeps interrupting you mid sentence",
        "script": "If someone keeps interrupting you mid sentence, they don't care what you think. They're waiting for their turn. Not listening. Planning. Your voice is just noise to them. Follow for more.",
        "search": ["two people talking dark", "person arguing dark", "conversation dark room"],
        "pin": "Tag someone who NEVER lets you finish 😤"
    },
    {
        "topic": "raises one eyebrow when you speak",
        "script": "If someone raises one eyebrow when you speak, they don't believe you. One eyebrow is doubt. Both eyebrows is surprise. One means they already caught the lie. Follow for more.",
        "search": ["person eyebrow raised dark", "skeptical face dark", "face close up dark portrait"],
        "pin": "🤨 Did you just make this face? Tag someone"
    },
    {
        "topic": "always sits facing the door",
        "script": "If someone always sits facing the door, they don't feel safe. Their subconscious needs an exit. This is not habit. It's survival mode. They've been trapped before. Follow for more.",
        "search": ["person sitting alone dark room", "dark doorway", "person back against wall dark"],
        "pin": "Do you do this? Be honest 👀"
    },
    {
        "topic": "clears their throat before they answer",
        "script": "If someone clears their throat before they answer your question, they're buying time. Their brain is editing the truth. The real answer came first. What you hear is version two. Follow for more.",
        "search": ["person thinking dark", "face close up dark speaking", "person nervous dark room"],
        "pin": "You've seen someone do this. Tag them 👀"
    },
    {
        "topic": "smiles but their eyes don't move",
        "script": "If someone smiles but their eyes don't change, that smile is fake. Real smiles move the eyes first. Fake smiles only move the mouth. The eyes always tell the truth. Follow for more.",
        "search": ["fake smile dark portrait", "person smiling dark", "eyes close up dark"],
        "pin": "Can YOU spot a fake smile? 🤔"
    },
    {
        "topic": "always talks about themselves",
        "script": "If someone always talks about themselves, they're not confident. They're starving for validation. Every story about them is a test. They need you to be impressed. That's not strength. It's hunger. Follow for more.",
        "search": ["person talking dark", "narcissist dark portrait", "person speaking dark room"],
        "pin": "We ALL know someone like this 😂"
    },
    {
        "topic": "checks the time while you talk",
        "script": "If someone checks the time while you're talking, they already left the conversation. Their body is still there but their mind is planning their exit. You're just filling silence for them. Follow for more.",
        "search": ["person checking watch dark", "wristwatch dark", "bored person dark room"],
        "pin": "This one hurts. Tag someone 😤"
    },
    {
        "topic": "nods too fast when you explain",
        "script": "If someone nods too fast when you're explaining something, they're not understanding you. They want you to stop talking. Fast nodding is a shutdown signal. Their brain checked out. Follow for more.",
        "search": ["person nodding dark", "conversation dark room", "person listening dark"],
        "pin": "You've seen this. Be honest 😂"
    },
    {
        "topic": "whispers to someone after talking to you",
        "script": "If someone whispers to another person right after talking to you, you were the topic. They smiled to your face and started talking the moment you turned around. That's not friendship. That's performance. Follow for more.",
        "search": ["people whispering dark", "gossip dark room", "two people talking secretly dark"],
        "pin": "This is why trust issues exist 💔"
    },
    {
        "topic": "stops smiling when you look away",
        "script": "If someone stops smiling the second you look away, that smile was never for you. It was for control. They want you to think they're kind. But kindness doesn't disappear when no one's watching. Follow for more.",
        "search": ["fake smile dark", "person looking away dark", "mask face dark portrait"],
        "pin": "The real ones stay the same when no one's watching 💯"
    },
    {
        "topic": "walks faster when they see you",
        "script": "If someone walks faster when they see you coming, they're not in a hurry. They're avoiding you. Their body made a decision before their brain did. You make them uncomfortable. Follow for more.",
        "search": ["person walking fast dark", "person avoiding dark street", "walking away dark"],
        "pin": "Ouch. Tag someone 😂"
    },
    {
        "topic": "changes the subject when you get serious",
        "script": "If someone changes the subject every time you get serious, they can't handle your truth. They want the fun version of you. Not the real one. That's not love. That's entertainment. Follow for more.",
        "search": ["couple talking dark", "serious conversation dark", "person looking away dark room"],
        "pin": "This one hit different 💔 Tag someone"
    },
    {
        "topic": "only calls you when they need something",
        "script": "If someone only calls you when they need something, you're not their friend. You're their tool. The moment you stop being useful, you'll stop hearing from them. That's not a bond. It's a transaction. Follow for more.",
        "search": ["person on phone dark", "lonely person dark room", "phone ringing dark"],
        "pin": "We all have that ONE person 😤"
    },
    {
        "topic": "laughs louder when someone else is watching",
        "script": "If someone laughs louder when someone else is watching, they're performing. The laugh isn't for you. It's for the audience. They need witnesses to prove they're having fun. Follow for more.",
        "search": ["person laughing dark group", "fake laughter dark", "social gathering dark"],
        "pin": "Social media in real life 😂"
    },
    {
        "topic": "says your name too much in conversation",
        "script": "If someone says your name too much during a conversation, they're trying to control you. Repeating your name creates a false sense of intimacy. It's a sales tactic. Not affection. Follow for more.",
        "search": ["person talking close dark", "manipulation dark portrait", "conversation dark intense"],
        "pin": "Did you notice this before? 👀"
    },
    {
        "topic": "remembers everything you said months ago",
        "script": "If someone remembers everything you said months ago, pay attention. Either they truly care about you, or they're collecting evidence to use against you later. Both exist. Know the difference. Follow for more.",
        "search": ["person thinking dark room", "memory dark portrait", "person staring dark"],
        "pin": "Which one is it? Comment below 👀"
    },
]

def load_config():
    with open(PROJECT / 'config' / 'config.yaml') as f:
        return yaml.safe_load(f)

# ── Voice Generation ──
async def generate_voice(script_text, output_dir, voice_params=None):
    """Generate voiceover + subtitles from script. Accepts voice rotation params."""
    import edge_tts
    
    if voice_params:
        voice = voice_params.get('voice', 'en-US-ChristopherNeural')
        rate = voice_params.get('rate', '-8%')
        pitch = voice_params.get('pitch', '-5Hz')
        print(f"  🎤 Voice: {voice_params.get('id', 'unknown')} rate={rate} pitch={pitch}")
    else:
        voice = 'en-US-ChristopherNeural'
        rate = '-8%'
        pitch = '-5Hz'
    
    comm = edge_tts.Communicate(text=script_text, voice=voice, rate=rate, pitch=pitch)
    audio_chunks = []
    word_boundaries = []
    
    async for chunk in comm.stream():
        if chunk['type'] == 'audio':
            audio_chunks.append(chunk['data'])
        elif chunk['type'] == 'WordBoundary':
            word_boundaries.append({
                'text': chunk['text'],
                'offset': chunk['offset'],
                'duration': chunk['duration']
            })
    
    mp3_path = output_dir / 'voiceover.mp3'
    with open(mp3_path, 'wb') as f:
        for d in audio_chunks:
            f.write(d)
    
    # Generate SRT
    srt_path = output_dir / 'subtitles.srt'
    entries = []
    for i, wb in enumerate(word_boundaries):
        s_ms = max(wb['offset'] // 10000, 100)
        e_ms = (wb['offset'] + wb['duration']) // 10000
        h1, r = divmod(s_ms, 3600000); m1, r = divmod(r, 60000); s1, ms1 = divmod(r, 1000)
        h2, r = divmod(e_ms, 3600000); m2, r = divmod(r, 60000); s2, ms2 = divmod(r, 1000)
        entries.append(
            f'{i+1}\n{int(h1):02d}:{int(m1):02d}:{int(s1):02d},{int(ms1):03d} --> '
            f'{int(h2):02d}:{int(m2):02d}:{int(s2):02d},{int(ms2):03d}\n{wb["text"].upper()}\n'
        )
    with open(srt_path, 'w') as f:
        f.write('\n'.join(entries))
    
    # Get duration
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp3_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    print(f"  🎤 Voice: {len(word_boundaries)} words, {duration:.1f}s")
    return duration

# ── Footage Download ──
def download_footage(queries, output_dir, num_clips=3):
    """Download portrait stock footage from Pexels."""
    import requests
    API_KEY = 'znl7TB689G7oboqJZabPGogC1u6EtjGSu1NyxdynBVbhKYNI03WusxKO'
    
    clips = []
    for q in queries:
        try:
            resp = requests.get('https://api.pexels.com/videos/search',
                headers={'Authorization': API_KEY},
                params={'query': q, 'per_page': 3, 'orientation': 'portrait', 'size': 'large'},
                timeout=15)
            if resp.status_code == 200:
                for v in resp.json().get('videos', []):
                    best = None
                    for vf in v.get('video_files', []):
                        w, h = vf.get('width', 0), vf.get('height', 0)
                        if h > w and w >= 720:
                            if best is None or w > best.get('width', 0):
                                best = vf
                    if best:
                        clips.append(best)
            if len(clips) >= num_clips:
                break
        except:
            pass
    
    downloaded = 0
    for i, c in enumerate(clips[:num_clips], 1):
        path = output_dir / f'clip_{i}.mp4'
        try:
            import requests as req
            r = req.get(c['link'], stream=True, timeout=120)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            sz = os.path.getsize(path) / (1024 * 1024)
            print(f"  📹 clip_{i}: {c.get('width', '?')}x{c.get('height', '?')} ({sz:.1f}MB)")
            downloaded += 1
        except:
            print(f"  ❌ clip_{i} failed")
    
    return downloaded

# ── Video Assembly ──
def assemble_video(temp_dir, output_path):
    """Assemble final video using the existing assemble_video.py."""
    # Copy clips to temp/
    project_temp = PROJECT / 'temp'
    for f in ['voiceover.mp3', 'subtitles.srt', 'clip_1.mp4', 'clip_2.mp4', 'clip_3.mp4']:
        src = temp_dir / f
        dst = project_temp / f
        if src.exists():
            import shutil
            shutil.copy2(src, dst)
    
    result = subprocess.run(
        ['python3', str(PROJECT / 'scripts' / 'assemble_video.py')],
        capture_output=True, text=True, cwd=str(PROJECT)
    )
    
    # Find the output file
    date_str = datetime.now().strftime('%Y-%m-%d')
    assembled = PROJECT / 'output' / f'short_{date_str}.mp4'
    if assembled.exists():
        import shutil
        shutil.move(str(assembled), str(output_path))
        size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  🎬 Assembled: {size:.1f}MB")
        return True
    else:
        print(f"  ❌ Assembly failed")
        if result.stderr:
            print(f"     {result.stderr[-200:]}")
        return False

# ── Upload ──
def upload_and_publish(video_path, title, description, tags, pin_comment, delay_min=5):
    """Upload as unlisted, wait for HD, then publish."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    
    creds = Credentials.from_authorized_user_file(
        str(PROJECT / 'config' / 'youtube_token.json'),
        ['https://www.googleapis.com/auth/youtube.upload',
         'https://www.googleapis.com/auth/youtube.force-ssl',
         'https://www.googleapis.com/auth/youtube']
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(PROJECT / 'config' / 'youtube_token.json', 'w') as f:
            f.write(creds.to_json())
    
    youtube = build('youtube', 'v3', credentials=creds)
    
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "22",
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en"
        },
        "status": {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False}
    }
    
    media = MediaFileUpload(str(video_path), chunksize=2*1024*1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    print(f"  📤 Uploading as UNLISTED...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"     {int(status.progress()*100)}%")
    
    video_id = response['id']
    url = f"https://youtube.com/shorts/{video_id}"
    print(f"  ✅ Uploaded: {url}")
    
    # Thumbnail (compressed to under 2MB)
    try:
        thumb = PROJECT / 'output' / 'thumb_temp.jpg'
        subprocess.run([
            'ffmpeg', '-y', '-i', str(video_path), '-ss', '0.5',
            '-frames:v', '1', '-update', '1', '-vf', 'scale=1080:1920',
            '-q:v', '5', str(thumb)
        ], capture_output=True)
        if thumb.exists() and os.path.getsize(thumb) < 2*1024*1024:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb), mimetype='image/jpeg')
            ).execute()
            print(f"  🖼️  Thumbnail set!")
    except:
        pass
    
    # Pinned comment
    try:
        youtube.commentThreads().insert(part="snippet", body={
            "snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": pin_comment}}}
        }).execute()
        print(f"  📌 Pinned: {pin_comment}")
    except:
        pass
    
    # Subscribe CTA comment
    try:
        youtube.commentThreads().insert(part="snippet", body={
            "snippet": {"videoId": video_id, "topLevelComment": {"snippet": {
                "textOriginal": "If this hit different, SUBSCRIBE — new psychology facts every day 🧠🔔"
            }}}
        }).execute()
        print(f"  🔔 Subscribe CTA added")
    except:
        pass
    
    # Wait for HD processing
    print(f"  ⏳ Waiting {delay_min} min for HD processing...")
    time.sleep(delay_min * 60)
    
    # Go PUBLIC
    youtube.videos().update(part="status", body={
        "id": video_id,
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }).execute()
    print(f"  🔓 NOW PUBLIC: {url}")
    
    return video_id, url

# ── AI Script Generation ──
def generate_ai_script(topic_hint, niche='psychology', config=None):
    """Generate a script using AI with God-Level SAECS prompt."""
    glp = GodLevelPrompts(niche=niche)
    prompt = glp.generate_script_prompt(topic_hint)
    
    cfg = config or load_config()
    
    # Try Ollama first
    if cfg.get('ai', {}).get('ollama_enabled', True):
        try:
            url = cfg['ai'].get('ollama_url', 'http://localhost:11434')
            resp = requests.post(
                f"{url}/api/generate",
                json={'model': cfg['ai'].get('ollama_model', 'llama3.2'),
                      'prompt': prompt, 'stream': False, 'format': 'json'},
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                result = json.loads(data.get('response', '{}'))
                if result.get('full_script'):
                    print(f"  🧠 AI script generated via Ollama")
                    return result
        except Exception as e:
            print(f"  ⚠️  Ollama failed: {e}")
    
    # Fallback to Groq
    groq_key = cfg.get('ai', {}).get('groq_api_key', '')
    if groq_key and not groq_key.startswith('YOUR'):
        try:
            resp = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
                json={
                    'model': cfg['ai'].get('groq_model', 'llama-3.3-70b-versatile'),
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.8,
                    'max_tokens': 1024,
                    'response_format': {'type': 'json_object'}
                },
                timeout=60
            )
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                result = json.loads(content)
                if result.get('full_script'):
                    print(f"  🧠 AI script generated via Groq")
                    return result
        except Exception as e:
            print(f"  ⚠️  Groq failed: {e}")
    
    return None


# ── Script Validation ──
def validate_script(script_text, title='', niche='psychology', config=None,
                   attempt=1, max_attempts=3, previous_rejection=None):
    """
    Run the God-Level Validation AI on a script.
    Returns (approved: bool, validation_result: dict)
    """
    glp = GodLevelPrompts(niche=niche)
    prompt = glp.generate_validation_prompt(
        script_text=script_text,
        title=title,
        attempt_number=attempt,
        max_attempts=max_attempts,
        previous_rejection=previous_rejection
    )
    
    cfg = config or load_config()
    result = None
    
    # Try Ollama
    if cfg.get('ai', {}).get('ollama_enabled', True):
        try:
            url = cfg['ai'].get('ollama_url', 'http://localhost:11434')
            resp = requests.post(
                f"{url}/api/generate",
                json={'model': cfg['ai'].get('ollama_model', 'llama3.2'),
                      'prompt': prompt, 'stream': False, 'format': 'json'},
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                result = json.loads(data.get('response', '{}'))
        except Exception as e:
            print(f"  ⚠️  Validation via Ollama failed: {e}")
    
    # Fallback to Groq
    if not result:
        groq_key = cfg.get('ai', {}).get('groq_api_key', '')
        if groq_key and not groq_key.startswith('YOUR'):
            try:
                resp = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': cfg['ai'].get('groq_model', 'llama-3.3-70b-versatile'),
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,  # Low temp for consistent judging
                        'max_tokens': 1024,
                        'response_format': {'type': 'json_object'}
                    },
                    timeout=60
                )
                if resp.status_code == 200:
                    content = resp.json()['choices'][0]['message']['content']
                    result = json.loads(content)
            except Exception as e:
                print(f"  ⚠️  Validation via Groq failed: {e}")
    
    if not result:
        # If both fail, auto-approve to not block pipeline
        print(f"  ⚠️  Validation AI unavailable — auto-approving")
        return True, {'verdict': 'APPROVE', 'overall_score': 0, 'auto_approved': True}
    
    verdict = result.get('verdict', 'APPROVE').upper()
    score = result.get('weighted_average', result.get('overall_score', 0))
    
    return verdict == 'APPROVE', result


def run_validation_loop(topic_hint, niche='psychology', config=None, max_attempts=3):
    """
    Generate script → validate → retry loop.
    Returns (topic_dict, validation_result) or (None, None) on total failure.
    """
    cfg = config or load_config()
    previous_rejection = None
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n  🔄 Attempt {attempt}/{max_attempts}")
        
        # Generate script
        ai_result = generate_ai_script(topic_hint, niche=niche, config=cfg)
        if not ai_result:
            print(f"  ❌ AI script generation failed on attempt {attempt}")
            continue
        
        script = ai_result.get('full_script', '')
        title = ai_result.get('title', f'If someone {topic_hint}… 🔴')
        
        print(f"  📝 Script ({ai_result.get('word_count', len(script.split()))} words): {script[:80]}...")
        
        # Validate
        approved, validation = validate_script(
            script_text=script,
            title=title,
            niche=niche,
            config=cfg,
            attempt=attempt,
            max_attempts=max_attempts,
            previous_rejection=previous_rejection
        )
        
        score = validation.get('weighted_average', validation.get('overall_score', '?'))
        
        if approved:
            print(f"  ✅ APPROVED (score: {score})")
            if validation.get('praise'):
                print(f"  💬 {validation['praise'][:100]}")
            
            # Build topic dict from AI result
            topic = {
                'topic': topic_hint,
                'script': script,
                'search': ai_result.get('search_queries', [f'person {topic_hint.split()[0]} dark', 'dark portrait', 'person dark room']),
                'pin': ai_result.get('pin_comment', 'What do you think? 👀'),
                'title': title,
                'validation_score': score,
            }
            return topic, validation
        else:
            reason = validation.get('rejection_reason', 'Did not meet quality standards')
            print(f"  ❌ REJECTED (score: {score}): {reason[:100]}")
            if validation.get('rewrite_instructions'):
                print(f"  📋 Rewrite: {validation['rewrite_instructions'][:100]}")
            previous_rejection = reason
    
    print(f"  💀 All {max_attempts} attempts failed for '{topic_hint}'")
    return None, None


# ── Main ──
def main():
    parser = argparse.ArgumentParser(description='AutoShorts PRO Pipeline — God-Level Edition')
    parser.add_argument('topic', nargs='*', help='Topic text (optional, uses random if omitted)')
    parser.add_argument('--ai', action='store_true', help='Use AI to generate script from trends')
    parser.add_argument('--dry-run', action='store_true', help='Test pipeline without uploading')
    parser.add_argument('--niche', default='psychology', help='Channel niche (psychology, data_storytelling, science, tech)')
    parser.add_argument('--validate', action='store_true', default=True, help='Enable script validation (default: on)')
    parser.add_argument('--no-validate', action='store_true', help='Skip script validation')
    parser.add_argument('--from-manifest', type=str, help='JSON manifest from n8n workflow')
    parser.add_argument('--max-retries', type=int, default=3, help='Max validation retry attempts')
    args = parser.parse_args()
    
    config = load_config()
    
    # ── Mode 1: From n8n manifest ──
    if args.from_manifest:
        try:
            manifest = json.loads(args.from_manifest)
            topic = {
                'topic': manifest.get('title', 'AI Generated'),
                'script': manifest['full_script'],
                'search': manifest.get('search_queries', ['dark portrait', 'person dark room']),
                'pin': manifest.get('pin_comment', 'What do you think? 👀'),
            }
            title = manifest.get('title', topic['topic'])
            print(f"\n{'='*60}")
            print(f"🎯 FROM N8N MANIFEST: {title}")
            print(f"   Validation Score: {manifest.get('validation_score', 'N/A')}")
            print(f"{'='*60}")
        except Exception as e:
            print(f"❌ Invalid manifest JSON: {e}")
            return 1
    
    # ── Mode 2: AI-generated script with validation ──
    elif args.ai:
        topic_hint = ' '.join(args.topic) if args.topic else random.choice([
            t['topic'] for t in PROVEN_TOPICS
        ])
        
        print(f"\n{'='*60}")
        print(f"🧠 GOD-LEVEL AI MODE: Generating script for '{topic_hint}'")
        print(f"   Niche: {args.niche} | Max retries: {args.max_retries}")
        print(f"{'='*60}")
        
        topic, validation = run_validation_loop(
            topic_hint=topic_hint,
            niche=args.niche,
            config=config,
            max_attempts=args.max_retries
        )
        
        if not topic:
            print(f"\n  ⚡ Falling back to PROVEN_TOPICS...")
            topic = random.choice(PROVEN_TOPICS)
            print(f"  📋 Using proven topic: {topic['topic']}")
        
        title = topic.get('title', f"If someone {topic['topic']}… 🔴")
    
    # ── Mode 3: Manual topic (original behavior) ──
    else:
        if args.topic:
            topic_text = ' '.join(args.topic)
            topic = None
            for t in PROVEN_TOPICS:
                if topic_text.lower() in t['topic'].lower():
                    topic = t
                    break
            if not topic:
                topic = {
                    "topic": topic_text,
                    "script": f"If someone {topic_text}, pay attention. Their body is telling you something their mouth never will. Watch carefully next time.",
                    "search": [f"person {topic_text.split()[0]} dark", "dark portrait face", "person dark room"],
                    "pin": "Be honest… did you think of someone? 👀"
                }
        else:
            topic = random.choice(PROVEN_TOPICS)
        
        title = f"If someone {topic['topic']}… 🔴"
        
        # Validate even manual topics (unless --no-validate)
        if not args.no_validate:
            print(f"\n🔍 Validating script...")
            approved, validation = validate_script(
                script_text=topic['script'],
                title=title,
                niche=args.niche,
                config=config
            )
            score = validation.get('weighted_average', validation.get('overall_score', '?'))
            if approved:
                print(f"  ✅ APPROVED (score: {score})")
            else:
                print(f"  ⚠️  Score: {score} — proceeding anyway (proven topic)")
    
    print(f"\n{'='*60}")
    print(f"🎯 TOPIC: {title}")
    print(f"{'='*60}")
    
    # Create temp workdir
    work_dir = PROJECT / 'temp' / f"pro_{datetime.now().strftime('%H%M%S')}"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Voice (with rotation)
    print("\n📢 STEP 1: Generating voice...")
    tracker = TopicTracker()
    voice_params = tracker.get_next_voice()
    duration = asyncio.run(generate_voice(topic['script'], work_dir, voice_params=voice_params))
    if duration > 18:
        print(f"  ⚠️  Too long ({duration:.1f}s) — trimming script...")
        words = topic['script'].split()
        topic['script'] = ' '.join(words[:int(len(words) * 0.7)])
        duration = asyncio.run(generate_voice(topic['script'], work_dir, voice_params=voice_params))
    
    # Step 2: Footage
    print("\n📹 STEP 2: Downloading footage...")
    clips = download_footage(topic['search'], work_dir)
    if clips < 3:
        print(f"  ⚠️  Only {clips} clips — downloading fallbacks...")
        download_footage(["dark person portrait", "shadow face dark", "person alone dark"], work_dir, 3 - clips)
    
    # Step 3: Assembly
    print("\n🎬 STEP 3: Assembling video...")
    output_path = PROJECT / 'output' / f"pro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    success = assemble_video(work_dir, output_path)
    if not success:
        print("❌ FAILED — could not assemble video")
        return 1
    
    # Step 4: Upload (skip on dry-run)
    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"🏁 DRY RUN COMPLETE — video saved but NOT uploaded")
        print(f"📁 {output_path}")
        print(f"📋 Title: {title}")
        print(f"📝 Script: {topic['script'][:100]}...")
        print(f"⏱️  Duration: {duration:.1f}s")
        print(f"{'='*60}")
        return 0
    
    print("\n📤 STEP 4: Uploading to YouTube...")
    description = (
        f"{topic['script']}\n\n"
        f"👆 Double tap if you agree\n"
        f"🔔 SUBSCRIBE for daily dark psychology facts\n"
        f"🧠 Follow @BrainyBooPsych\n\n"
        f"#Shorts #DarkPsychology #BodyLanguage #PsychologyFacts "
        f"#ManipulationTactics #ReadPeople #HumanBehavior #BrainyBoo "
        f"#ToxicPeople #MentalHealth #DarkPsychologyFacts #PsychologyShorts "
        f"#NarcissistSigns #Gaslighting #EmotionalAbuse #Manipulation\n\n"
        f"dark psychology, body language, psychology facts, manipulation tactics, "
        f"how to read people, brainy boo, psychology shorts 2026, narcissist signs"
    )
    tags = ["dark psychology", "body language", "psychology facts", "manipulation",
            "read people", "brainy boo", "shorts", topic['topic'].split()[0]]
    
    video_id, url = upload_and_publish(output_path, title, description, tags, topic['pin'])
    
    print(f"\n{'='*60}")
    print(f"🎉 COMPLETE!")
    print(f"🔗 {url}")
    print(f"📋 Title: {title}")
    print(f"⏱️  Duration: {duration:.1f}s")
    if topic.get('validation_score'):
        print(f"📊 Validation Score: {topic['validation_score']}")
    print(f"{'='*60}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
