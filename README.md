# Kerala Cafe News (keralacafenews.com)

Malayalam news headline site for Kerala. Pulls headlines from RSS feeds every 30 minutes,
shows a short snippet, thumbnail and a link to the original article.
Readers can sort by **Latest** (date) or **Hot**. Ad slots are built in.
Free to host. No server, no database.

## Files
- `index.html` – the website (Malayalam interface)
- `feeds.json` – your news sources, category rules and hot-score settings
- `fetch_news.py` – downloads feeds, groups the same story from different outlets, writes `news.json`
- `.github/workflows/update.yml` – runs the script every 30 minutes on GitHub
- `news.json` – headlines shown by the site (auto-generated; the one included is sample data)
- `CNAME` – tells GitHub Pages to serve the site on keralacafenews.com

## How "Hot" works
Each story gets a score = (number of different outlets reporting it × 3) + a recency boost that
halves every 8 hours. Stories covered by several outlets rise to the top, and fresh stories beat old ones.
Stories are matched by headline similarity. Tune `hot.similarity` (lower = groups more) in `feeds.json`.
The site has no visitor-view data, so this is "most reported", not "most clicked".

## Launch (about 15 minutes, free)
1. Create a free GitHub account and a new **public** repository.
2. Upload all files in this folder (keep the `.github` folder).
3. **Settings → Pages:** branch `main`, folder `/ (root)`, Save.
4. **Actions → Update news → Run workflow** once. After that it runs by itself every 30 minutes.
5. **Connect your domain keralacafenews.com** at your domain registrar's DNS settings:
   - four `A` records for `@` pointing to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - one `CNAME` record for `www` pointing to `YOURNAME.github.io`
   (If GitHub has changed these, its "Custom domain" help page shows the current values.)
   Then in Settings → Pages tick **Enforce HTTPS** once the certificate is ready.

## Adding more Kerala sources
Add a line to `feeds.json`:
`{ "source": "Name", "category": "Kerala", "url": "https://.../rss" }`
Most Malayalam outlets (Manorama, Madhyamam, Deshabhimani, MediaOne, Kerala Kaumudi, Mangalam,
24 News, Reporter) have an RSS page linked in their footer. Check each outlet's terms for RSS use.
Feeds that fail only show up as `FAIL` in the Action log; the rest keep working.
The category comes from the article's URL (see `urlCategoryMap`), so one feed can fill many tabs.

## Make money
1. **Pages Google wants before AdSense approval:** About, Privacy Policy, Contact, Disclaimer.
   Replace the `#` links in the footer.
2. **Add original Malayalam content.** AdSense rejects sites that only list other sites' headlines.
   Publish 15-30 original pieces in your own words: daily summaries, explainers, local stories.
3. **Apply to Google AdSense**, paste its script into the commented block in `<head>`,
   and replace the "Ad space" boxes with your ad units. Add the `ads.txt` file AdSense gives you.
4. **Share on social media:** WhatsApp is the biggest channel in Kerala. Every card has share buttons.
   Post links to your own pages, not only to the source links.
5. While waiting for approval: affiliate links, a WhatsApp channel or newsletter.

## Rules to keep the site safe
- Keep only headline + short snippet + link. Do not paste full articles.
- Keep the "read at source" links so readers go back to the publisher.
- Remove any source that asks you to stop using its feed.
