#!/usr/bin/env python3
"""
StackMaster Tech - Buttercup Games dataset generator
=====================================================
Produces the exact dataset used in the "Splunk Search & Event Analysis"
handbook by Vivek Arora:

  * access_combined.log  -> index=web       sourcetype=access_combined
  * linux_secure.log     -> index=security  sourcetype=linux_secure
  * products.csv         -> lookup: productId -> product_name, price, categoryId

Timestamps are anchored to "now" and span the previous 7 whole days, so the
book's  earliest=-7d@d  / "Last 7 days"  examples light up immediately.

Re-run any time to refresh the time window:
    python3 generate_buttercup_data.py --web 6000 --sec 500
"""

import argparse
import csv
import random
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# Product catalogue  (productId, product_name, categoryId, price)
# Categories match the handbook: STRATEGY, ARCADE, SHOOTER, TEE
# SG-G01 / WC-SH-A01 and the 24.99 / 39.99 prices appear verbatim in the book.
# ----------------------------------------------------------------------
PRODUCTS = [
    ("SG-G01",    "Mediocre Kingdoms",      "STRATEGY", 24.99),
    ("PZ-SG-G05", "SIM Cubicle",            "STRATEGY", 19.99),
    ("DB-SG-G01", "Benign Space Debris",    "ARCADE",   24.99),
    ("FS-SG-G03", "Final Sequel",           "ARCADE",   14.99),
    ("WC-SH-A01", "Dream Crusher",          "SHOOTER",  39.99),
    ("WC-SH-A02", "Orvil the Wolverine",    "SHOOTER",  29.99),
    ("WC-SH-T02", "World of Cheese Tee",    "TEE",       9.99),
    ("MB-AG-T01", "Manganiello Bros. Tee",  "TEE",      11.99),
]

ACTIONS = ["view", "view", "view", "view", "addtocart", "addtocart",
           "purchase", "purchase", "remove"]          # weighted
STATUS_OK = [200, 200, 200, 200, 200, 200, 200, 304]  # weighted toward 200
STATUS_ERR = [404, 404, 500, 503]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X)",
    "Mozilla/5.0 (Linux; Android 14)",
]
PAGES = ["/product.screen", "/category.screen", "/cart.do",
         "/checkout.do", "/home", "/search.do"]
REFERERS = [
    "http://buttercupgames.com/home",
    "http://buttercupgames.com/cart.do",
    "http://buttercupgames.com/category.screen",
    "https://www.google.com/",
    "-",
]


def rand_ip():
    # public-looking client IPs
    return f"{random.randint(23,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def sessid():
    import string
    return "SD" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(14))


def gen_web(n, start, end):
    span = (end - start).total_seconds()
    rows = []
    # a pool of returning visitors + sessions
    visitors = [rand_ip() for _ in range(max(40, n // 60))]
    for _ in range(n):
        ts = start + timedelta(seconds=random.random() * span)
        # business-hours weighting: nudge toward 9-18
        if random.random() < 0.55:
            ts = ts.replace(hour=random.randint(9, 18),
                            minute=random.randint(0, 59),
                            second=random.randint(0, 59))
        ip = random.choice(visitors)
        pid, pname, cat, price = random.choice(PRODUCTS)
        action = random.choice(ACTIONS)
        page = "/product.screen" if action in ("view", "addtocart", "purchase", "remove") else random.choice(PAGES)
        status = random.choice(STATUS_ERR) if random.random() < 0.06 else random.choice(STATUS_OK)
        nbytes = 0 if status in (304,) else random.randint(600, 5200)
        rtime = random.randint(80, 900)
        jsid = sessid()
        ua = random.choice(USER_AGENTS)
        ref = random.choice(REFERERS)
        # query string carries the KV pairs Splunk auto-extracts at search time
        qs = (f"productId={pid}&action={action}&categoryId={cat}"
              f"&price={price}&JSESSIONID={jsid}")
        uri = f"{page}?{qs}"
        line = (f'{ip} - - [{ts.strftime("%d/%b/%Y:%H:%M:%S")} +0000] '
                f'"GET {uri} HTTP/1.1" {status} {nbytes} '
                f'"{ref}" "{ua}" {rtime}')
        rows.append((ts, line))
    rows.sort(key=lambda r: r[0])
    return [r[1] for r in rows]


def gen_security(n, start, end):
    span = (end - start).total_seconds()
    hosts = ["web01", "web02", "db01", "app01"]
    good_users = ["ecommerce", "deploy", "svc_backup", "vivek"]
    bad_users = ["admin", "root", "test", "oracle", "postgres", "guest"]
    good_ips = ["10.11.2.34", "10.11.2.51", "192.168.14.7"]
    rows = []

    for _ in range(n):
        ts = start + timedelta(seconds=random.random() * span)
        host = random.choice(hosts)
        pid = random.randint(1000, 65000)
        port = random.randint(1024, 65535)
        if random.random() < 0.55:
            user = random.choice(good_users)
            ip = random.choice(good_ips)
            line = (f'{ts.strftime("%b %e %H:%M:%S")} {host} sshd[{pid}]: '
                    f'Accepted password for {user} from {ip} port {port} ssh2')
        else:
            user = random.choice(bad_users)
            ip = rand_ip()
            line = (f'{ts.strftime("%b %e %H:%M:%S")} {host} sshd[{pid}]: '
                    f'Failed password for invalid user {user} from {ip} port {port} ssh2')
        rows.append((ts, line))

    # ---- inject a clean brute-force burst so the streamstats 5m>=5 example fires
    burst_ip = "203.0.113.7"
    burst_host = "web01"
    burst_start = end - timedelta(hours=6)
    for i in range(14):
        ts = burst_start + timedelta(seconds=i * 15)   # 14 tries in ~3.5 min
        pid = random.randint(1000, 65000)
        port = random.randint(40000, 60000)
        line = (f'{ts.strftime("%b %e %H:%M:%S")} {burst_host} sshd[{pid}]: '
                f'Failed password for invalid user admin from {burst_ip} port {port} ssh2')
        rows.append((ts, line))
    # attacker finally succeeds once (nice for correlation demos)
    ts = burst_start + timedelta(seconds=14 * 15 + 20)
    rows.append((ts, f'{ts.strftime("%b %e %H:%M:%S")} {burst_host} sshd[{random.randint(1000,65000)}]: '
                     f'Accepted password for admin from {burst_ip} port {random.randint(40000,60000)} ssh2'))

    rows.sort(key=lambda r: r[0])
    return [r[1] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", type=int, default=6000, help="web access events")
    ap.add_argument("--sec", type=int, default=500, help="security events")
    ap.add_argument("--days", type=int, default=7, help="days of history")
    args = ap.parse_args()

    now = datetime.now()
    start = (now - timedelta(days=args.days)).replace(microsecond=0)

    web = gen_web(args.web, start, now)
    sec = gen_security(args.sec, start, now)

    with open("access_combined.log", "w") as f:
        f.write("\n".join(web) + "\n")
    with open("linux_secure.log", "w") as f:
        f.write("\n".join(sec) + "\n")
    with open("products.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["productId", "product_name", "categoryId", "price"])
        for pid, name, cat, price in PRODUCTS:
            w.writerow([pid, name, cat, price])

    print(f"access_combined.log : {len(web)} events")
    print(f"linux_secure.log    : {len(sec)} events")
    print(f"products.csv        : {len(PRODUCTS)} products")
    print(f"time window         : {start:%Y-%m-%d %H:%M} -> {now:%Y-%m-%d %H:%M}")


if __name__ == "__main__":
    main()
