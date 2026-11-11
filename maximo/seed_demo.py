"""Demo data for the App Connect labs: three completed pump work orders at BEDFORD with labour and material actuals,
charged to the pump station cost centre (GL 6000-200-???). Lab A posts their costs to the ERP.

Re-runnable: a work order is created only if none with the same description exists; actuals are added only while
the work order has none. Uses the Manage REST API (MXAPIWODETAIL).

    set MAXIMO_API=https://<manage-host>/maximo/api
    set MAXIMO_APIKEY=<an administrator's API key, for the demo data only>
    python seed_demo.py
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE, KEY = os.environ["MAXIMO_API"].rstrip("/"), os.environ["MAXIMO_APIKEY"]
SITE, GL = "BEDFORD", "6000-200-???"
# asset, description, labour code, craft, hours, item, quantity
WORK = [
    ("AH005", "Pump AH005 bearing replacement after high vibration", "ADAMS", "MECH", 2.5, "12853", 1),
    ("AH001", "Pump AH001 mechanical seal leak, replace seal", "ADAMS", "MECH", 4.0, "117084", 2),
    ("AH003", "Pump AH003 realign pump and motor coupling", "ADAMS", "MECH", 3.0, "10112", 4),
    ("AH007", "Pump AH007 replace worn impeller", "ADAMS", "MECH", 5.0, "12853", 1),
]


def call(method, path, body=None, headers=None):
    h = {"apikey": KEY, "Accept": "application/json", "Content-Type": "application/json"}
    h.update(headers or {})
    r = urllib.request.Request(BASE + path, method=method, headers=h,
                               data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            t = f.read()
            return f.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def find(where, select):
    q = urllib.parse.urlencode({"lean": 1, "oslc.select": select, "oslc.where": where, "oslc.pageSize": 50})
    c, r = call("GET", "/os/mxapiwodetail?" + q)
    if c != 200:
        raise SystemExit(f"query failed {c} {json.dumps(r)[:300]}")
    return r.get("member", [])


def patch(rid, body, extra=""):
    return call("POST", f"/os/mxapiwodetail/{rid}?lean=1{extra}", body, {"x-method-override": "PATCH", "patchtype": "MERGE"})


for asset, desc, labor, craft, hrs, item, qty in WORK:
    hit = find(f'siteid="{SITE}" and description="{desc}"', "wonum,status,href,actlabcost")
    if not hit:
        c, r = call("POST", "/os/mxapiwodetail?lean=1", {"siteid": SITE, "description": desc, "assetnum": asset,
                    "worktype": "CM", "wopriority": 2, "glaccount": GL}, {"properties": "wonum,href"})
        if c not in (200, 201):
            raise SystemExit(f"create failed {c} {json.dumps(r)[:300]}")
        hit = [{"wonum": r["wonum"], "href": r["href"], "status": "WAPPR", "actlabcost": 0}]
    wo = hit[0]
    rid = wo["href"].rsplit("/", 1)[1]
    if wo["status"] == "WAPPR":
        patch(rid, {"status": "APPR"}, "&action=wsmethod:changeStatus")
    if not float(wo.get("actlabcost") or 0):
        c, r = patch(rid, {"glaccount": GL,
                           "labtrans": [{"laborcode": labor, "craft": craft, "regularhrs": hrs, "startdate": "2026-11-10T08:00:00+00:00"}],
                           "matusetrans": [{"itemnum": item, "storeloc": "CENTRAL", "quantity": qty, "issuetype": "ISSUE"}]})
        if c not in (200, 204):
            raise SystemExit(f"actuals failed on {wo['wonum']}: {c} {json.dumps(r)[:300]}")
    if wo["status"] != "COMP":
        c, r = patch(rid, {"status": "COMP", "memo": "Work done"}, "&action=wsmethod:changeStatus")
        if c not in (200, 204):
            raise SystemExit(f"complete failed on {wo['wonum']}: {c} {json.dumps(r)[:300]}")
    print(wo["wonum"], asset, "COMP with actuals")
