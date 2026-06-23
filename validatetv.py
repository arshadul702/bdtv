import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target URLs: Can be a folder tree, a direct raw file, or main repo URL
TARGET_SOURCES = [
    "https://raw.githubusercontent.com/abusaeeidx/Mrgify-BDIX-IPTV/refs/heads/main/playlist.m3u",
    "https://raw.githubusercontent.com/imShakil/tvlink/refs/heads/main/all.m3u",
    "https://raw.githubusercontent.com/ashik4u/mrgify-clean/refs/heads/main/playlist.m3u",
]

def smart_crawl_github():
    print("🤖 Starting Smart GitHub URL analyzer...")
    raw_file_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in TARGET_SOURCES:
        url_clean = url.strip()
        if "raw.githubusercontent.com" in url_clean:
            raw_file_urls.append(url_clean)
            continue
            
        try:
            response = requests.get(url_clean, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
                
            if "/blob/" in url_clean:
                raw_url = url_clean.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                raw_file_urls.append(raw_url)
            elif "/tree/" in url_clean or url_clean.count('/') <= 4:
                all_paths = re.findall(r'href="([^"]+)"', response.text)
                for path in all_paths:
                    if "/blob/" in path and any(ext in path.lower() for ext in ['.m3u', '.m3u8']):
                        raw_url = f"https://raw.githubusercontent.com{path}".replace("/blob/", "/")
                        raw_file_urls.append(raw_url)
            else:
                raw_file_urls.append(url_clean)
        except Exception as e:
            print(f"❌ Failed processing target {url_clean}: {e}")
            
    return list(set(raw_file_urls))

def extract_unique_sports_links():
    all_raw_files = smart_crawl_github()
    print(f"📋 Total parsed raw playlist files to scan: {len(all_raw_files)}")
    
    raw_links = []
    for count, file_url in enumerate(all_raw_files):
        if count >= 40: # Safety cap for files
            break
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(file_url, headers=headers, timeout=10)
            if response.status_code == 200:
                found_links = re.findall(r'(https?://[^\s"\'\>]+)', response.text)
                raw_links.extend(found_links)
        except:
            pass

    filtered_links = []
    for link in raw_links:
        clean_url = link.strip().split('#')[0].split('"')[0].split("'")[0]
        if any(ext in clean_url.lower() for ext in ['.m3u8', '.ts', '.mpd', '/live', '/stream']) or "sports" in clean_url.lower():
            filtered_links.append(clean_url)

    unique_links = list(set(filtered_links))
    print(f"📊 Total raw streams scraped: {len(raw_links)}")
    print(f"🎯 Total UNIQUE streams left for verification: {len(unique_links)}")
    return unique_links

def is_stream_live(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        # Fast HEAD request
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code in [200, 201, 206]:
            return url, True
    except:
        try:
            # Fallback strict GET request
            response = requests.get(url, headers=headers, timeout=3, stream=True)
            if response.status_code in [200, 201, 206]:
                return url, True
        except:
            pass
    return url, False

def main():
    unique_sports_urls = extract_unique_sports_links()
    valid_streams = []
    
    # Target capacity for final playlist
    max_channels = 150 
    
    print(f"⚡ Starting high-speed Multi-threaded validation (20 concurrent workers)...")
    
    # Using ThreadPoolExecutor for concurrent network requests
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all validation tasks to the pool
        future_to_url = {executor.submit(is_stream_live, url): url for url in unique_sports_urls}
        
        for future in as_completed(future_to_url):
            if len(valid_streams) >= max_channels:
                print(f"Target reached ({max_channels} active lines). Cancelling remaining tasks.")
                break
                
            try:
                url, is_live = future.result()
                if is_live:
                    print(f"[LIVE] -> {url}")
                    valid_streams.append(url)
            except Exception as e:
                pass

    # Output playlist generation
    if valid_streams:
        with open("sports.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i, stream_url in enumerate(valid_streams):
                f.write(f"#EXTINF:-1 tvg-id='Sports-{i+1}' tvg-name='Sports {i+1}',Live Sports {i+1}\n")
                f.write(f"{stream_url}\n")
        print(f"✅ Success! sports.m3u8 updated with {len(valid_streams)} clean unique active streams.")
    else:
        print("❌ Script closed. No streams passed active network filters.")

if __name__ == "__main__":
    main()
