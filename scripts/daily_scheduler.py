#!/usr/bin/env python3
"""
AutoShorts Daily Scheduler — Smart Edition.

Strategy:
  - 2 videos/day, 8-hour gap (7 AM + 3 PM IST)
  - ONE consistent voice (brand identity)
  - Trending topics (Groq AI generates based on what's viral NOW)
  - Quality gating (no filler, no weak hooks)
  - UNLISTED → 5 min → PUBLIC

Usage:
  python3 scripts/daily_scheduler.py --slot 1     # Morning upload
  python3 scripts/daily_scheduler.py --slot 2     # Afternoon upload
  python3 scripts/daily_scheduler.py --dry-run    # Test mode
  python3 scripts/daily_scheduler.py --stats      # Analytics
"""

import json, os, sys, random, subprocess, time, re, asyncio, requests, yaml
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

from topic_tracker import TopicTracker

# ─── BRAND IDENTITY (consistent across ALL videos) ───
BRAND = {
    "voice": "en-US-GuyNeural",
    "rate": "-8%",
    "pitch": "-6Hz",
    "highlight_color": (255, 30, 30, 255),     # Deep red
    "text_color": (255, 255, 255, 255),         # White
    "bg_color": (0, 0, 0, 200),                # Dark box
    "font_size": 130,                           # BIG
    "category_id": "27",                        # Education
}

UPLOAD_SLOTS = {
    1: {"label": "Morning (USA Prime Time)", "hour": 7},
    2: {"label": "Afternoon (USA Early Morning)", "hour": 15},
}


def load_config():
    with open(PROJECT / 'config' / 'config.yaml') as f:
        return yaml.safe_load(f)


def generate_trending_topic(cfg):
    """Use Groq AI to generate a TRENDING viral topic."""
    groq_key = cfg.get('ai', {}).get('groq_api_key', '')
    if not groq_key:
        return fallback_topic()
    
    prompt = """You are a YouTube Shorts trend analyst. Generate ONE viral dark psychology / stoicism topic that would get millions of views RIGHT NOW in the USA.

The topic must follow these PROVEN viral patterns:
- Numbered lists: "7 dark habits...", "5 signs someone...", "3 stoic rules..."
- Power dynamics: silence, respect, fear, dominance
- "Anti-victim" framing: protect yourself from manipulation
- "Secret knowledge" framing: things they never told you
- Emotional triggers: betrayal, loneliness, toxic people, narcissists

Return ONLY valid JSON:
{"topic": "the viral topic as it would appear in a title", "script_prompt": "detailed prompt to write a 120-140 word script on this topic", "pexels_queries": ["query1", "query2", "query3", "query4"]}"""

    try:
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0.9, 'max_tokens': 300},
            timeout=30
        )
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            raw = re.sub(r'[\x00-\x1f\x7f]', ' ', content)
            s, e = raw.find('{'), raw.rfind('}') + 1
            if s >= 0 and e > s:
                return json.loads(raw[s:e])
    except Exception as ex:
        print(f"  ⚠️  Trending topic error: {ex}")
    
    return fallback_topic()


def fallback_topic():
    """Fallback trending topics if AI fails."""
    topics = [
        {"topic": "7 dark signs someone secretly fears you", "script_prompt": "Write about 7 behaviors that reveal someone is intimidated by you", "pexels_queries": ["dark silhouette power", "confident person standing", "eyes close up fear", "shadow portrait"]},
        {"topic": "5 stoic rules that make you impossible to manipulate", "script_prompt": "Write about 5 ancient stoic principles reframed as modern defense tactics against manipulation", "pexels_queries": ["roman statue dark", "person meditating calm", "chess strategy", "man walking alone powerful"]},
        {"topic": "The one sentence narcissists can't handle hearing", "script_prompt": "Write about a specific response that completely disarms narcissistic behavior", "pexels_queries": ["person arguing couple", "calm face closeup", "silence portrait dark", "walking away confident"]},
    ]
    return random.choice(topics)


def generate_script(topic_data, cfg):
    """Generate a viral-ready script using Groq AI."""
    groq_key = cfg.get('ai', {}).get('groq_api_key', '')
    
    prompt = f"""You are an elite viral psychology Shorts scriptwriter. Your videos get 1M-7M views.

TOPIC: {topic_data['topic']}
DIRECTION: {topic_data.get('script_prompt', 'Write a compelling psychology script')}

RULES:
1. EXACTLY 120-140 words. Count them. Not one more.
2. First sentence = SCROLL STOPPER. Bold, provocative, unexpected.
3. If it's a numbered list, each point = 1-2 short punchy sentences.
4. NO filler: no "in this video", no "let me explain", no "studies show that"
5. End with a TWIST that connects back to the opening (loop for replays).
6. Tone: commanding, mysterious, like a dark documentary narrator.
7. Frame as EDUCATIONAL self-protection, not manipulation advice.
8. Include a subtle CTA at the end like "Follow if you see the pattern."

Return ONLY JSON (no newlines in string values):
{{"full_script": "the complete script flowing naturally", "title": "catchy title with emoji, under 55 chars", "pin_comment": "question that forces viewers to comment"}}"""

    try:
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0.8, 'max_tokens': 500},
            timeout=30
        )
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            raw = re.sub(r'[\x00-\x1f\x7f]', ' ', content)
            s, e = raw.find('{'), raw.rfind('}') + 1
            if s >= 0 and e > s:
                data = json.loads(raw[s:e])
                wc = len(data.get('full_script', '').split())
                print(f"  📝 Script: {wc} words — '{data.get('title', '')}'")
                return data
    except Exception as ex:
        print(f"  ⚠️  Script error: {ex}")
    
    return None


def generate_voice(script_text, work_dir):
    """Generate voice with brand-consistent settings."""
    import edge_tts
    
    async def _gen():
        comm = edge_tts.Communicate(text=script_text, voice=BRAND['voice'], 
                                     rate=BRAND['rate'], pitch=BRAND['pitch'])
        audio, wbs = [], []
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                audio.append(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                wbs.append({'text': chunk['text'], 'offset': chunk['offset'], 'duration': chunk['duration']})
        
        mp3 = f'{work_dir}/voice.mp3'
        with open(mp3, 'wb') as f:
            for d in audio:
                f.write(d)
        
        if not wbs:
            r = subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',mp3], capture_output=True, text=True)
            total = float(r.stdout.strip())
            words = script_text.split()
            tpw = total / max(len(words), 1)
            for i, w in enumerate(words):
                wbs.append({'text': w, 'offset': int(i*tpw*1e7), 'duration': int(tpw*1e7*0.9)})
        
        # SRT — 2 words per group
        entries = []
        idx, i = 1, 0
        while i < len(wbs):
            gs = min(2, len(wbs) - i)
            grp = wbs[i:i+gs]
            text = ' '.join(w['text'] for w in grp).upper()
            s_ms = max(grp[0]['offset']//10000, 100)
            e_ms = (grp[-1]['offset']+grp[-1]['duration'])//10000
            h1,r2=divmod(s_ms,3600000); m1,r2=divmod(r2,60000); s1,ms1=divmod(r2,1000)
            h2,r2=divmod(e_ms,3600000); m2,r2=divmod(r2,60000); s2,ms2=divmod(r2,1000)
            entries.append(f'{idx}\n{int(h1):02d}:{int(m1):02d}:{int(s1):02d},{int(ms1):03d} --> {int(h2):02d}:{int(m2):02d}:{int(s2):02d},{int(ms2):03d}\n{text}\n')
            idx += 1; i += gs
        
        with open(f'{work_dir}/subs.srt', 'w') as f:
            f.write('\n'.join(entries))
        
        r = subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',mp3], capture_output=True, text=True)
        return float(r.stdout.strip()), len(entries)
    
    return asyncio.run(_gen())


def download_footage(queries, work_dir, pexels_key):
    """Download portrait stock footage from Pexels."""
    clips = []
    for q in queries[:4]:
        try:
            r = requests.get('https://api.pexels.com/videos/search',
                headers={'Authorization': pexels_key},
                params={'query': q, 'per_page': 2, 'orientation': 'portrait', 'size': 'medium'}, timeout=15)
            if r.status_code != 200:
                continue
            for vid in r.json().get('videos', [])[:1]:
                best = None
                for vf in vid.get('video_files', []):
                    if vf.get('height', 0) >= 720:
                        if not best or vf['height'] > best.get('height', 0):
                            best = vf
                if best:
                    cp = f'{work_dir}/clip_{len(clips)}.mp4'
                    cr = requests.get(best['link'], timeout=60)
                    if cr.status_code == 200:
                        with open(cp, 'wb') as f:
                            f.write(cr.content)
                        clips.append(cp)
                        print(f"     ⬇️  {q[:25]}... ✅")
        except:
            pass
    return clips


def assemble_video(work_dir, duration, output_path):
    """Assemble final video with brand subtitles + music."""
    W, H = 1080, 1920
    
    # Crop clips
    clips = [f for f in os.listdir(work_dir) if f.startswith('clip_')]
    cropped = []
    for ci, cp in enumerate(sorted(clips)):
        src = f'{work_dir}/{cp}'
        dst = f'{work_dir}/cr_{ci}.mp4'
        probe = subprocess.run(['ffprobe','-v','quiet','-show_entries','stream=width,height','-of','csv=p=0:s=x','-select_streams','v:0',src], capture_output=True, text=True)
        try:
            sw, sh = [int(x) for x in probe.stdout.strip().split('x')]
        except:
            sw, sh = 1920, 1080
        vf = f"scale=-2:{H},crop={W}:{H},setsar=1" if sw > sh else f"scale={W}:-2,crop={W}:{H},setsar=1"
        r = subprocess.run(['ffmpeg','-y','-i',src,'-vf',vf,'-c:v','h264_videotoolbox','-q:v','65','-an','-pix_fmt','yuv420p','-t','15',dst], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            cropped.append(dst)
    
    if not cropped:
        return False
    
    # Concat
    concat = f'{work_dir}/concat.mp4'
    cl = f'{work_dir}/cl.txt'
    total = 0
    with open(cl, 'w') as f:
        while total < duration + 2:
            for c in cropped:
                f.write(f"file '{os.path.abspath(c)}'\n")
                total += 8
                if total >= duration + 2:
                    break
    subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',cl,'-t',str(duration+1),'-c:v','h264_videotoolbox','-q:v','65','-an','-pix_fmt','yuv420p',concat], capture_output=True, timeout=120)
    
    # Subtitle PNGs (brand style)
    subs = []
    with open(f'{work_dir}/subs.srt') as f:
        content = f.read().strip()
    for block in re.split(r'\n\s*\n', content):
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            ts = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
            if ts:
                g = ts.groups()
                s = int(g[0])*3600+int(g[1])*60+int(g[2])+int(g[3])/1000
                e = int(g[4])*3600+int(g[5])*60+int(g[6])+int(g[7])/1000
                subs.append({'start': s, 'end': e, 'text': ' '.join(lines[2:]).strip()})
    
    font = None
    for fp in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/System/Library/Fonts/Helvetica.ttc']:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, BRAND['font_size'])
                break
            except:
                continue
    
    sub_pngs = []
    for si, sub in enumerate(subs):
        img = Image.new('RGBA', (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        text = sub['text']
        af = font
        bbox = draw.textbbox((0,0), text, font=af)
        tw = bbox[2]-bbox[0]
        if tw > W - 100:
            sc = max(int(BRAND['font_size'] * (W-100) / tw), 70)
            try:
                af = ImageFont.truetype(font.path, sc)
            except:
                pass
        bbox = draw.textbbox((0,0), text, font=af)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        tx, ty = (W-tw)//2, (H//2)-(th//2)
        
        draw.rounded_rectangle([tx-25, ty-25, tx+tw+25, ty+th+25], radius=18, fill=BRAND['bg_color'])
        for ox in range(-5,6):
            for oy in range(-5,6):
                if abs(ox)+abs(oy) > 3:
                    draw.text((tx+ox,ty+oy), text, font=af, fill=(0,0,0,255))
        
        words = text.split()
        wx = tx
        for wi, word in enumerate(words):
            c = BRAND['highlight_color'] if wi == 0 else BRAND['text_color']
            draw.text((wx, ty), word, font=af, fill=c)
            wb = draw.textbbox((0,0), word+' ', font=af)
            wx += wb[2]-wb[0]
        
        pp = f'{work_dir}/s_{si}.png'
        img.save(pp)
        sub_pngs.append({'path': pp, 'start': sub['start'], 'end': sub['end']})
    
    # Final assembly
    inputs = ['-i', concat, '-i', f'{work_dir}/voice.mp3']
    fp = []
    oc = '[0:v]'
    for si, sp in enumerate(sub_pngs):
        inputs.extend(['-i', sp['path']])
        idx = si + 2
        out = f'[v{si}]'
        fp.append(f"{oc}[{idx}:v]overlay=0:0:enable='between(t,{sp['start']:.2f},{sp['end']:.2f})'{out}")
        oc = out
    
    music = str(PROJECT / 'assets' / 'music' / 'dark_ambient.mp3')
    inputs.extend(['-i', music])
    mi = len(sub_pngs) + 2
    af_str = f'[1:a]volume=1.0[voice];[{mi}:a]volume=0.10[mus];[voice][mus]amix=inputs=2:duration=first[aout]'
    ff = ';'.join(fp) + ';' + af_str
    
    cmd = ['ffmpeg','-y',*inputs,'-filter_complex',ff,'-map',oc,'-map','[aout]',
           '-c:v','h264_videotoolbox','-q:v','50','-profile:v','high',
           '-c:a','aac','-b:a','192k','-pix_fmt','yuv420p',
           '-t',str(min(duration+1,58)),'-shortest',output_path]
    
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        # Fallback no subs
        cmd2 = ['ffmpeg','-y','-i',concat,'-i',f'{work_dir}/voice.mp3','-i',music,
                '-filter_complex','[1:a]volume=1.0[v];[2:a]volume=0.10[m];[v][m]amix=inputs=2:duration=first[a]',
                '-map','0:v','-map','[a]','-c:v','h264_videotoolbox','-q:v','50',
                '-c:a','aac','-b:a','192k','-pix_fmt','yuv420p','-t',str(min(duration+1,58)),'-shortest',output_path]
        subprocess.run(cmd2, capture_output=True, timeout=120)
    
    return os.path.exists(output_path)


def upload_to_youtube(video_path, title, description, tags, pin_comment):
    """Upload as UNLISTED → 5 min → PUBLIC."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    
    creds = Credentials.from_authorized_user_file(str(PROJECT / 'config' / 'youtube_token.json'),
        ['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.force-ssl','https://www.googleapis.com/auth/youtube'])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(PROJECT / 'config' / 'youtube_token.json', 'w') as f:
            f.write(creds.to_json())
    
    yt = build('youtube', 'v3', credentials=creds)
    
    body = {"snippet": {"title": title[:100], "description": description[:5000], "tags": tags,
                        "categoryId": BRAND['category_id'], "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False}}
    
    media = MediaFileUpload(video_path, chunksize=2*1024*1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    
    print(f"  📤 Uploading UNLISTED...")
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
    
    vid_id = resp['id']
    url = f"https://youtube.com/shorts/{vid_id}"
    print(f"  ✅ Uploaded: {url}")
    
    # Thumbnail
    try:
        thumb = f'{os.path.dirname(video_path)}/thumb.jpg'
        subprocess.run(['ffmpeg','-y','-i',video_path,'-ss','1','-frames:v','1','-vf','scale=1080:1920','-q:v','5',thumb], capture_output=True)
        if os.path.exists(thumb):
            yt.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumb, mimetype='image/jpeg')).execute()
    except:
        pass
    
    # Pin comment
    try:
        yt.commentThreads().insert(part="snippet", body={
            "snippet": {"videoId": vid_id, "topLevelComment": {"snippet": {"textOriginal": pin_comment}}}
        }).execute()
        print(f"  📌 Pinned: {pin_comment[:40]}...")
    except:
        pass
    
    # Wait 5 min for HD
    print(f"  ⏳ 5 min HD wait...")
    time.sleep(300)
    
    # PUBLIC
    yt.videos().update(part="status", body={"id": vid_id, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}).execute()
    print(f"  🔓 PUBLIC: {url}")
    
    return vid_id, url


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AutoShorts — 2/Day Smart Scheduler')
    parser.add_argument('--slot', type=int, choices=[1, 2], help='Upload slot (1=morning, 2=afternoon)')
    parser.add_argument('--dry-run', action='store_true', help='Test without uploading')
    parser.add_argument('--stats', action='store_true', help='Show analytics')
    args = parser.parse_args()
    
    tracker = TopicTracker()
    cfg = load_config()
    pexels_key = cfg.get('background_video', {}).get('pexels_api_key', '')
    
    if args.stats:
        stats = tracker.get_stats()
        print(f"📊 Total uploads: {stats['total_uploads']}")
        print(f"   Unique topics: {stats['unique_topics']}")
        print(f"   Avg score: {stats['avg_validation_score']}")
        return
    
    slot = args.slot or 1
    print(f"\n{'='*60}")
    print(f"🎬 SLOT {slot}: {UPLOAD_SLOTS[slot]['label']}")
    print(f"   Time: {datetime.now().strftime('%H:%M IST')}")
    print(f"{'='*60}")
    
    # Step 1: Get trending topic
    print(f"\n  🔍 Finding trending topic...")
    topic_data = generate_trending_topic(cfg)
    print(f"  📝 Topic: {topic_data['topic']}")
    
    # Step 2: Generate script
    print(f"\n  🤖 Generating script...")
    script_data = generate_script(topic_data, cfg)
    if not script_data:
        print(f"  ❌ Script generation failed!")
        return
    
    script_text = script_data['full_script']
    title = script_data['title']
    pin = script_data.get('pin_comment', 'Which one hit different? 👀')
    
    # Step 3: Generate voice
    work_dir = str(PROJECT / 'temp' / f"slot_{slot}_{datetime.now().strftime('%H%M')}")
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"\n  🎤 Generating voice ({BRAND['voice']})...")
    dur, subs = generate_voice(script_text, work_dir)
    print(f"  ✅ Voice: {dur:.1f}s, {subs} subtitle groups")
    
    # Step 4: Download footage
    print(f"\n  📹 Downloading footage...")
    clips = download_footage(topic_data.get('pexels_queries', ['dark psychology']), work_dir, pexels_key)
    if not clips:
        print(f"  ❌ No footage!")
        return
    
    # Step 5: Assemble
    output_path = str(PROJECT / 'output' / f"short_{datetime.now().strftime('%Y%m%d_%H%M')}.mp4")
    print(f"\n  🎬 Assembling video...")
    if not assemble_video(work_dir, dur, output_path):
        print(f"  ❌ Assembly failed!")
        return
    
    sz = os.path.getsize(output_path) / (1024*1024)
    print(f"  ✅ Video: {sz:.1f}MB, {dur:.0f}s")
    
    if args.dry_run:
        print(f"\n  🏁 DRY RUN — video saved but not uploaded: {output_path}")
        return
    
    # Step 6: Upload
    desc = f"""{script_text}

🧠 Educational psychology content for self-improvement and self-protection.

#Shorts #DarkPsychology #Psychology #Stoicism #Manipulation #SelfImprovement #MentalHealth #HumanBehavior #Mindset #Viral

dark psychology, stoicism, manipulation, human behavior, self improvement, psychology facts"""
    
    tags = ["Shorts","Dark Psychology","Psychology","Stoicism","Manipulation","Self Improvement",
            "Mental Health","Human Behavior","Mindset","Psychology Facts","Viral"]
    
    vid_id, url = upload_to_youtube(output_path, title, desc, tags, pin)
    
    tracker.record_upload(topic=topic_data['topic'], script=script_text, title=title,
        voice_id='guy_neural', youtube_id=vid_id, youtube_url=url)
    
    print(f"\n  🎉 DONE! {url}")


if __name__ == '__main__':
    main()
