# Adding New Sites to Wohnung Scraper

This guide walks you through adding a new apartment listing site to the scraper.

## Quick Start

```bash
# Generate a template configuration
wohnung site new <site-name>

# Edit the configuration file
vim sites/<site-name>.yaml

# Validate your configuration
wohnung site validate sites/<site-name>.yaml

# Test with dry-run scraping
wohnung site test <site-name>
```

## Table of Contents

1. [Understanding Site Configurations](#understanding-site-configurations)
2. [Step-by-Step Guide](#step-by-step-guide)
3. [Selector Reference](#selector-reference)
4. [Marker Configuration](#marker-configuration)
5. [Pagination Setup](#pagination-setup)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## Understanding Site Configurations

Site configurations are YAML files that tell the scraper how to extract apartment data from a website. Each configuration contains:

- **Basic info**: Site name, URL, display name
- **Selectors**: CSS selectors for finding data
- **Markers** (optional): Keywords to detect in listings
- **Pagination** (optional): How to navigate multiple pages
- **Performance settings**: Timeouts and rate limiting

## Step-by-Step Guide

### Step 1: Inspect the Target Website

1. **Open the site** in your browser
2. **Right-click** on an apartment listing and select "Inspect" or "Inspect Element"
3. **Identify the structure**:
   - What element wraps each apartment? (the `listing` selector)
   - Where is the title? Price? Location?
   - How are multiple pages linked?

### Step 2: Generate Template

```bash
wohnung site new immoscout24
```

This creates `sites/immoscout24.yaml` with all required fields.

### Step 3: Fill in Basic Information

```yaml
name: immoscout24  # Unique identifier (lowercase, no spaces)
display_name: "ImmobilienScout24"  # Human-readable name
base_url: "https://www.immobilienscout24.de/Suche/de/wohnung-mieten"
enabled: true  # Set to false to temporarily disable
```

**Naming conventions:**
- `name`: Use lowercase with hyphens for multi-word names
- `display_name`: Can include spaces, capitals, and special characters

### Step 4: Configure Selectors

This is the most important part. You need CSS selectors for:

#### Required Selectors

```yaml
selectors:
  # Container for each apartment (required)
  listing: "article.result-list-entry"

  # Apartment title (required)
  title: "h5.result-list-entry__brand-title"

  # Link to detail page (required, must have href attribute)
  url: "a.result-list-entry__brand-title-container"

  # Location/address (required)
  location: "div.result-list-entry__address"
```

#### Optional Selectors

```yaml
  # Monthly rent
  price: "dd.result-list-entry__primary-criterion"

  # Living space in m²
  size: "dd.result-list-entry__secondary-criterion:nth-of-type(1)"

  # Number of rooms
  rooms: "dd.result-list-entry__secondary-criterion:nth-of-type(2)"

  # Description text
  description: "p.result-list-entry__criteria"

  # Main image (src attribute)
  image: "img.gallery-image"
```

**Tips:**
- Use browser DevTools to test selectors: `$$('your-selector')` in console
- Start generic, then add specificity if needed
- Use class names, not IDs (IDs might be dynamic)
- Test selectors on multiple pages to ensure consistency

### Step 5: Add Markers (Optional)

Markers help identify special apartment types or features:

```yaml
markers:
  - name: vormerkung_possible  # Internal ID
    label: "Vormerkung möglich"  # Display name
    patterns:  # Search terms (case-insensitive)
      - "vormerkung möglich"
      - "vormerken"
      - "vormerkung"
    priority: high  # high | medium | low
    search_in:  # Where to search
      - title
      - description
```

**Priority levels:**
- `high`: Critical features (🔴 red badge in emails)
- `medium`: Important features (🟡 yellow badge)
- `low`: Nice-to-have features (⚪ gray badge)

**Pattern matching:**
- Exact substring match by default
- Use regex for complex patterns: `"\\d+ zimmer"` matches "3 zimmer", "4 zimmer"
- Always case-insensitive

### Step 6: Configure Pagination (Optional)

For multi-page results:

**Option A: URL Pattern**
```yaml
pagination:
  enabled: true
  max_pages: 5  # Maximum pages to scrape
  url_pattern: "?pagenumber={page}"  # Page 2: ?pagenumber=2
```

**Option B: Next Button**
```yaml
pagination:
  enabled: true
  max_pages: 5
  next_selector: "a.next-page"  # Selector for "next page" link
```

### Step 7: Set Performance Options

```yaml
request_timeout: 30  # Seconds (5-120)
rate_limit_delay: 1.0  # Seconds between requests (0.1-10.0)
```

**Guidelines:**
- Use longer delays for smaller sites
- Respect robots.txt
- Start with conservative settings

### Step 8: Validate Configuration

```bash
wohnung site validate sites/immoscout24.yaml
```

This checks:
- ✅ YAML syntax is valid
- ✅ All required fields are present
- ✅ Selectors follow CSS syntax
- ✅ URLs are valid
- ⚠️  Warnings for potential issues

### Step 9: Test Scraping

```bash
# Dry run (no data saved)
wohnung site test immoscout24

# With verbose output
wohnung site test immoscout24 --verbose

# Limit pages
wohnung site test immoscout24 --max-pages 1
```

### Step 10: Enable and Run

Once everything works:

```yaml
enabled: true
```

Then run the scraper:

```bash
wohnung scrape
```

## Selector Reference

### CSS Selector Basics

```css
/* Element type */
div, article, h2

/* Class */
.apartment-card, .listing

/* ID (avoid - usually dynamic) */
#listing-12345

/* Attribute */
a[href*="/apartment/"]
img[src]

/* Descendant */
.card h3  /* h3 inside .card */

/* Direct child */
.card > h3  /* h3 directly under .card */

/* Multiple classes */
.card.active.featured

/* Nth-of-type */
div:nth-of-type(2)  /* Second div */

/* Contains text */
span:contains('Price')
```

### Finding Elements in DevTools

1. Right-click element → "Inspect"
2. In Elements panel, right-click the tag → "Copy" → "Copy selector"
3. Test in Console: `$$('paste-selector-here')`
4. Simplify the selector (remove IDs, reduce specificity)

### Common Pitfalls

❌ **Too specific:**
```yaml
listing: "#main > div.container > div.content > article.card-12345"
```

✅ **Just right:**
```yaml
listing: "article.apartment-card"
```

❌ **Dynamic IDs:**
```yaml
url: "#listing-abc123"  # Changes per page
```

✅ **Use classes or attributes:**
```yaml
url: "a.listing-link"
```

## Marker Configuration

### Use Cases

**Availability status:**
```yaml
- name: immediate_availability
  label: "Sofort verfügbar"
  patterns: ["sofort verfügbar", "ab sofort"]
  priority: high
```

**Property features:**
```yaml
- name: furnished
  label: "Möbliert"
  patterns: ["möbliert", "möblierte", "voll möbliert"]
  priority: medium
```

**Special conditions:**
```yaml
- name: subsidized
  label: "Gefördert"
  patterns: ["gefördert", "wohnberechtigungsschein", "wbs"]
  priority: high
```

### Regex Patterns

For date matching:
```yaml
patterns:
  - "verfügbar ab \\d{2}\\.\\d{2}\\.\\d{4}"  # "verfügbar ab 01.03.2026"
```

For number ranges:
```yaml
patterns:
  - "\\b[3-5] zimmer"  # Matches 3, 4, or 5 rooms
```

**Important:**
- Escape backslashes in YAML: `\\d` not `\d`
- Use `\\b` for word boundaries

## Pagination Setup

### Pattern-Based Pagination

**Sequential numbers:**
```yaml
url_pattern: "/page/{page}"
# Results: /page/2, /page/3, ...
```

**Query parameters:**
```yaml
url_pattern: "?page={page}&sort=date"
# Results: ?page=2&sort=date, ?page=3&sort=date
```

**Custom formats:**
```yaml
url_pattern: "/apartments-p{page}.html"
# Results: /apartments-p2.html, /apartments-p3.html
```

### Next-Button Pagination

When pages use "Next" links:
```yaml
pagination:
  enabled: true
  next_selector: "a.pagination-next"  # Link with href to next page
  max_pages: 10
```

### Hybrid Approach

If URL pattern exists but you want a safety check:
```yaml
pagination:
  enabled: true
  url_pattern: "?page={page}"
  next_selector: "a.next-page"  # Stop if this disappears
  max_pages: 5
```

## Troubleshooting

### Problem: No apartments found

**Check:**
1. Is `listing` selector correct?
   ```bash
   # In browser console on the site:
   $$('your-listing-selector').length  # Should be > 0
   ```

2. Is the site using JavaScript to load content?
   - This scraper uses static HTML only
   - If content loads via AJAX, consider using a different approach

3. Try with `--verbose` flag:
   ```bash
   wohnung site test yoursite --verbose
   ```

### Problem: Missing data (price, size, etc.)

**Check:**
1. Are selectors specific enough?
2. Do they exist within the `listing` container?
3. Test each selector individually:
   ```javascript
   // In browser console
   document.querySelectorAll('.listing-card').forEach(card => {
     console.log('Title:', card.querySelector('h3.title').textContent);
     console.log('Price:', card.querySelector('.price').textContent);
   });
   ```

### Problem: Pagination not working

**Check:**
1. Does the pattern match actual URLs?
2. Is `max_pages` set high enough?
3. Does `next_selector` point to a link with href?

**Debug:**
```bash
wohnung site test yoursite --max-pages 2 --verbose
```

### Problem: Validation errors

```bash
wohnung site validate sites/yoursite.yaml
```

Common errors:
- **Invalid YAML syntax**: Check indentation (use spaces, not tabs)
- **Missing required fields**: Ensure listing, title, url, location are set
- **Invalid URLs**: Must start with http:// or https://
- **Invalid priority**: Must be 'low', 'medium', or 'high'

### Problem: Markers not detected

**Check:**
1. Is text actually in title/description fields?
2. Check case sensitivity (should be case-insensitive by default)
3. Test patterns:
   ```python
   # In Python
   text = "Vormerkung möglich"
   pattern = "vormerkung"
   print(pattern.lower() in text.lower())  # Should be True
   ```

4. Use test command:
   ```bash
   wohnung site test-markers yoursite --limit 20
   ```

## Best Practices

### 1. Start Simple

Begin with just required selectors:
```yaml
selectors:
  listing: ".apartment"
  title: "h2"
  url: "a.link"
  location: ".location"
```

Add optional ones after basic scraping works.

### 2. Test Incrementally

Don't fill everything out at once:
1. Configure basic info + required selectors → validate
2. Add optional selectors → test scraping
3. Add markers → test marker detection
4. Add pagination → test multiple pages

### 3. Use Descriptive Marker Names

❌ Bad:
```yaml
- name: m1
  label: "Thing 1"
```

✅ Good:
```yaml
- name: immediate_availability
  label: "Sofort verfügbar"
```

### 4. Document Site-Specific Quirks

Add comments to your YAML:
```yaml
# Note: This site loads prices via JavaScript after page load
# We can only scrape listings that have static pricing
selectors:
  price: ".price-static"  # Not .price-dynamic
```

### 5. Respect Website Policies

- Check `robots.txt`
- Use reasonable `rate_limit_delay` (1-2 seconds minimum)
- Don't set `max_pages` too high
- Only scrape publicly available data

### 6. Version Control

Keep configurations in git:
```bash
git add sites/yoursite.yaml
git commit -m "Add YourSite scraper configuration"
```

### 7. Regular Maintenance

Websites change. Set reminders to:
- Test configurations monthly
- Update selectors when sites redesign
- Adjust markers based on new terminology

## Examples

See `sites/` directory for complete examples:

- **[oevw.yaml](../sites/oevw.yaml)** - Active Austrian housing site
- **[immoscout24.yaml.example](../sites/immoscout24.yaml.example)** - German market leader
- **[wg-gesucht.yaml.example](../sites/wg-gesucht.yaml.example)** - Shared housing
- **[ebay-kleinanzeigen.yaml.example](../sites/ebay-kleinanzeigen.yaml.example)** - Classifieds
- **[immowelt.yaml.example](../sites/immowelt.yaml.example)** - German real estate portal
- **[willhaben.yaml.example](../sites/willhaben.yaml.example)** - Austrian marketplace

## Getting Help

If you're stuck:

1. **Check validation output:**
   ```bash
   wohnung site validate sites/yoursite.yaml
   ```

2. **Run verbose test:**
   ```bash
   wohnung site test yoursite --verbose
   ```

3. **View site info:**
   ```bash
   wohnung site info yoursite
   ```

4. **Check existing examples:**
   ```bash
   ls sites/
   ```

## Summary Checklist

Before considering a site configuration complete:

- [ ] Configuration validates without errors
- [ ] Test scraping returns apartments
- [ ] Required fields (title, url, location) are populated
- [ ] Optional fields (price, size, rooms) work where available
- [ ] Markers detect correctly (if configured)
- [ ] Pagination works (if configured)
- [ ] Rate limiting is respectful (1-2s minimum)
- [ ] Configuration is committed to git
- [ ] Site is enabled: `enabled: true`

---

**Ready to add your first site?**

```bash
wohnung site new <site-name>
```

Happy scraping! 🏠
