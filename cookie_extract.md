## Extracting and Converting Firefox Cookies for yt-dlp

### Why is this important?

YouTube has implemented measures to prevent automated access to their content, including subtitle downloads. These measures often require users to be logged in to access certain features or content. By using cookies from your browser where you're already logged into YouTube, we can authenticate our requests and bypass these restrictions.

For our YouTube Video Summarizer application, this is crucial because it allows us to download subtitles for a wider range of videos, including those that might require authentication. Without these cookies, our application might fail to retrieve subtitles for many videos, significantly limiting its functionality.

### Steps to Extract and Convert Firefox Cookies

1. **Locate your Firefox profile**:
   - Open Firefox and navigate to `about:profiles` in the address bar.
   - Look for the "Root Directory" of the profile you're currently using.

2. **Create a Python script to convert cookies**:
   Create a file named `convert_cookies.py` with the following content:

   ```python
   import sqlite3
   import http.cookiejar
   import os

   def convert_firefox_cookies(firefox_cookies_path, output_file):
       conn = sqlite3.connect(firefox_cookies_path)
       c = conn.cursor()

       cookie_jar = http.cookiejar.MozillaCookieJar(output_file)

       c.execute("SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE host LIKE '%youtube.com'")
       for row in c.fetchall():
           domain, path, secure, expires, name, value = row
           secure = bool(secure)
           cookie = http.cookiejar.Cookie(
               version=0, name=name, value=value,
               port=None, port_specified=False,
               domain=domain, domain_specified=bool(domain.startswith('.')),
               domain_initial_dot=domain.startswith('.'),
               path=path, path_specified=bool(path),
               secure=secure, expires=expires, discard=False,
               comment=None, comment_url=None, rest={}, rfc2109=False
           )
           cookie_jar.set_cookie(cookie)

       cookie_jar.save(ignore_discard=True, ignore_expires=True)

       conn.close()
       print(f"Cookies saved to {output_file}")

   firefox_cookies_path = os.path.expanduser('~/Library/Application Support/Firefox/Profiles/XXXXXXXX.default-release/cookies.sqlite')
   output_file = 'youtube_cookies.txt'

   convert_firefox_cookies(firefox_cookies_path, output_file)
   ```

   Replace `XXXXXXXX` in the `firefox_cookies_path` with your actual profile name.

3. **Run the script**:
   Execute the script by running:
   ```
   python convert_cookies.py
   ```
   This will create a `youtube_cookies.txt` file in the correct format for yt-dlp.

4. **Use the converted cookies in the application**:
   - Copy the `youtube_cookies.txt` file to your application directory.
   - Update your Dockerfile to include:
     ```dockerfile
     COPY youtube_cookies.txt /app/youtube_cookies.txt
     ```
   - Update your docker-compose.yml to mount the cookie file:
     ```yaml
     volumes:
       - ./youtube_cookies.txt:/app/youtube_cookies.txt:ro
     ```
   - In your `app.py`, ensure the path to the cookie file is correct:
     ```python
     ydl_opts = {
         # ... other options ...
         'cookiefile': '/app/youtube_cookies.txt',
     }
     ```

5. **Security and Maintenance**:
   - Keep your cookie file secure and do not share it, as it contains sensitive login information.
   - Cookies expire over time, so you may need to repeat this process periodically to refresh your cookies.

By following these steps, you'll be able to use your Firefox cookies with yt-dlp in the YouTube Video Summarizer application, allowing it to access and download subtitles for a wider range of videos, including those that require authentication.
