# Buttercup Games — Working Dataset

Companion dataset for the **Splunk Search & Event Analysis** handbook
(Vivek Arora · StackMaster Tech). Every SPL block in the book is copy‑paste
runnable against this data.

## What's in the box

| File | Purpose |
|------|---------|
| `access_combined.log` | ~6,000 web access events → **index=web**, **sourcetype=access_combined** |
| `linux_secure.log` | ~515 auth events → **index=security**, **sourcetype=linux_secure** (includes a brute‑force burst) |
| `products.csv` | product lookup: `productId → product_name, categoryId, price` |
| `stackmaster_buttercup/` | Splunk app: creates the two indexes + all field extractions + the product lookup |
| `generate_buttercup_data.py` | regenerate/resize the data and re‑anchor timestamps to “now” |

Timestamps span the **last 7 days up to now**, so the handbook’s
`earliest=-7d@d` / “Last 7 days” examples return data immediately.

---

## Fastest setup (single Splunk instance)

**1 — Install the app (indexes + field extractions + lookup)**

Copy the app folder into your Splunk apps directory and restart:

```bash
cp -r stackmaster_buttercup $SPLUNK_HOME/etc/apps/
$SPLUNK_HOME/bin/splunk restart
```

This creates the `web` and `security` indexes, the `access_combined` /
`linux_secure` field extractions, and the `productId → product_name` lookup.

**2 — Load the two log files (GUI, no config editing)**

In Splunk Web: **Settings → Add Data → Upload**.

* Upload `access_combined.log` → set **Source type = access_combined**,
  **Index = web** → Review → Submit.
* Upload `linux_secure.log` → set **Source type = linux_secure**,
  **Index = security** → Review → Submit.

That’s it — start searching.

> Prefer files on disk? Edit the paths in
> `stackmaster_buttercup/default/inputs.conf`, set `disabled = false`,
> drop the logs there, and restart instead of uploading.

---

## No‑app / quickest‑possible option

If you just want to explore without installing the app, upload both files as
above (pick any index, e.g. `main`). Because the URL carries `key=value`
pairs, Splunk auto‑extracts `action`, `productId`, `categoryId`, `price` and
`JSESSIONID` on its own. You’ll only miss `product_name` (needs the lookup)
and the tidy `linux_secure` fields (`user`, `src_ip`, `port`,
`vendor_action`) — install the app to get those.

---

## Validate the load

Run these — each should return rows:

```spl
index=web sourcetype=access_combined | stats count BY action, categoryId
index=web action=purchase | stats sum(price) AS revenue BY categoryId | sort - revenue
index=web | lookup buttercup_products productId OUTPUT product_name | stats count BY product_name
index=security sourcetype=linux_secure | stats count BY vendor_action
```

Brute‑force check (should surface `203.0.113.7` with fails ≥ 5) —
this is the Chapter 8 `streamstats` example:

```spl
index=security vendor_action="Failed password"
| sort 0 _time
| streamstats time_window=5m count AS fails_5m BY src_ip
| where fails_5m >= 5
| stats max(fails_5m) AS peak BY src_ip
| sort - peak
```

---

## Regenerate / resize

```bash
python3 generate_buttercup_data.py --web 10000 --sec 800 --days 14
```

Re‑running refreshes all timestamps to the current date, then re‑upload the
files (or let a monitor input pick them up).

---

## Field reference

**web / access_combined**

| Field | Example | Source |
|-------|---------|--------|
| `clientip` | 182.236.164.11 | access_combined builtin |
| `status` | 200, 404, 500, 503 | access_combined builtin |
| `bytes` | 3467 | access_combined builtin |
| `useragent`, `referer` | Mozilla/5.0 … | access_combined builtin |
| `action` | view, addtocart, purchase, remove | URL query (auto‑KV) |
| `productId` | SG-G01, WC-SH-A01 | URL query (auto‑KV) |
| `categoryId` | STRATEGY, ARCADE, SHOOTER, TEE | URL query (auto‑KV) |
| `price` | 24.99, 39.99 | URL query (auto‑KV) |
| `JSESSIONID` | SD1SL7FF6ADFF4953 | URL query (auto‑KV) |
| `product_name` | Mediocre Kingdoms | lookup on `productId` |

**security / linux_secure**

| Field | Example | Source |
|-------|---------|--------|
| `host` | web01 | linux_secure builtin |
| `user` | admin, ecommerce | app extraction |
| `src_ip` | 203.0.113.7 | app extraction |
| `port` | 52344 | app extraction |
| `vendor_action` | Failed password / Accepted password | app extraction |
