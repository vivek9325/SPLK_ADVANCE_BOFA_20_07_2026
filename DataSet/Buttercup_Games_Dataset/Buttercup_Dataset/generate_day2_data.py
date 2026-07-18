#!/usr/bin/env python3
"""Day 2 dataset extensions for the Field Extraction / Lookups handbook."""
import json, csv, random, string
from datetime import datetime, timedelta

random.seed(42)
PRODUCTS = [
    ("SG-G01","Mediocre Kingdoms","STRATEGY",24.99),
    ("PZ-SG-G05","SIM Cubicle","STRATEGY",19.99),
    ("DB-SG-G01","Benign Space Debris","ARCADE",24.99),
    ("FS-SG-G03","Final Sequel","ARCADE",14.99),
    ("WC-SH-A01","Dream Crusher","SHOOTER",39.99),
    ("WC-SH-A02","Orvil the Wolverine","SHOOTER",29.99),
    ("WC-SH-T02","World of Cheese Tee","TEE",9.99),
    ("MB-AG-T01","Manganiello Bros. Tee","TEE",11.99),
]
CITIES = [  # city, country, lat, lon
    ("Austin","US",30.27,-97.74),("San Jose","US",37.34,-121.89),
    ("London","GB",51.51,-0.13),("Berlin","DE",52.52,13.40),
    ("Bengaluru","IN",12.97,77.59),("Sydney","AU",-33.87,151.21),
    ("Toronto","CA",43.65,-79.38),("Tokyo","JP",35.68,139.69),
]
LOYALTY=["none","silver","gold","platinum"]

def sid(): return "SD"+"".join(random.choice(string.ascii_uppercase+string.digits) for _ in range(14))
def ip(): return f"{random.randint(23,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def gen_json(n=140):
    now=datetime.now(); start=now-timedelta(days=7); span=(now-start).total_seconds()
    rows=[]
    for i in range(n):
        ts=start+timedelta(seconds=random.random()*span)
        k=random.randint(1,3); items=[]
        for _ in range(k):
            pid,name,cat,price=random.choice(PRODUCTS)
            items.append({"productId":pid,"name":name,"category":cat,"qty":random.randint(1,3),"price":price})
        total=round(sum(it["qty"]*it["price"] for it in items),2)
        city,country,lat,lon=random.choice(CITIES)
        ev={
            "ts":ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "event":"checkout",
            "orderId":f"ORD-{100000+i}",
            "JSESSIONID":sid(),
            "customer":{"clientip":ip(),"userId":f"u_{random.randint(1000,9999)}","loyalty":random.choice(LOYALTY)},
            "cart":{"items":items,"itemCount":sum(it["qty"] for it in items),"total":total,"currency":"USD"},
            "payment":{"method":random.choice(["card","paypal","upi"]),"status":random.choices(["approved","declined"],[0.9,0.1])[0]},
            "geo":{"country":country,"city":city,"lat":lat,"lon":lon}
        }
        rows.append((ts,json.dumps(ev)))
    rows.sort(key=lambda r:r[0])
    with open("checkout_events.json","w") as f:
        f.write("\n".join(r[1] for r in rows)+"\n")
    return len(rows)

def gen_multikv(n=40):
    """Tabular 'top processes' report events for multikv demos."""
    now=datetime.now(); start=now-timedelta(days=2); span=(now-start).total_seconds()
    hosts=["web01","web02","app01","db01"]
    procs=["splunkd","java","nginx","python3","postgres","node","sshd","kube-apiserver"]
    lines=[]
    rows=[]
    for _ in range(n):
        ts=start+timedelta(seconds=random.random()*span); host=random.choice(hosts)
        hdr=f"{ts.strftime('%Y-%m-%d %H:%M:%S')} {host} proc_report:"
        table="  PID   USER      CPU   MEM  COMMAND\n"
        for _ in range(5):
            table+=(f"  {random.randint(100,9999):<5} {random.choice(['root','splunk','www-data','postgres']):<9} "
                    f"{random.uniform(0.1,88):>4.1f} {random.uniform(0.5,42):>4.1f}  {random.choice(procs)}\n")
        rows.append((ts,hdr+"\n"+table.rstrip()))
    rows.sort(key=lambda r:r[0])
    with open("proc_report.log","w") as f:
        f.write("\n".join(r[1] for r in rows)+"\n")
    return len(rows)

def gen_lookups():
    with open("http_status_lookup.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["status","status_description","status_type"])
        for s,d,t in [(200,"OK","Success"),(206,"Partial Content","Success"),(301,"Moved Permanently","Redirect"),
                      (304,"Not Modified","Redirect"),(400,"Bad Request","Client Error"),(403,"Forbidden","Client Error"),
                      (404,"Not Found","Client Error"),(500,"Internal Server Error","Server Error"),
                      (502,"Bad Gateway","Server Error"),(503,"Service Unavailable","Server Error")]:
            w.writerow([s,d,t])
    # geo enrichment keyed on city (pairs with checkout geo / geospatial demo)
    with open("store_geo_lookup.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["city","country","lat","lon","region"])
        regions={"US":"Americas","CA":"Americas","GB":"EMEA","DE":"EMEA","IN":"APAC","AU":"APAC","JP":"APAC"}
        for city,country,lat,lon in CITIES:
            w.writerow([city,country,lat,lon,regions[country]])
    # denylist of known-bad source IPs (include/exclude demo on security index)
    with open("threat_ip_lookup.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["src_ip","threat_type","severity"])
        for ipa,t,sev in [("203.0.113.7","brute_force","high"),("198.51.100.22","scanner","medium"),
                          ("203.0.113.99","c2","critical"),("192.0.2.44","tor_exit","low")]:
            w.writerow([ipa,t,sev])

if __name__=="__main__":
    j=gen_json(); m=gen_multikv(); gen_lookups()
    print(f"checkout_events.json : {j} JSON events")
    print(f"proc_report.log      : {m} tabular events")
    print("lookups              : http_status_lookup.csv, store_geo_lookup.csv, threat_ip_lookup.csv")
