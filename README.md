# Maximo and IBM App Connect: costs to the ERP, field readings to condition monitoring

Code that goes with the IBM Community post *Maximo, the ERP and the plant floor in one flow: integrating Maximo with
IBM App Connect* (Maximo group), by Mohamed Chihaoui.

Two integrations between IBM Maximo Manage 9 and IBM App Connect Enterprise 13:

| Flow | What it does |
|---|---|
| `wo_cost_sync` | Every minute: finds completed work orders without an ERP journal number, posts one journal per work order (labour line + material line) to the ERP, writes the journal number to `EXTERNALREFID` and adds a work log entry. Each work order is posted once; failures are logged and retried next minute. |
| `field_readings` | HTTP service `POST /field/readings`: checks each reading from a field gateway (tag, unit, range), converts °C to °F and mm/s to in/s, loads it into the asset meter in Maximo, and answers with what was loaded and what was refused, with Maximo's own reason. Maximo's condition monitoring then creates work orders from job plans. |
| `erp_mock` | A stand-in for the ERP's journal API (`/erp/journals`, `/erp/outage`), so the lab runs without an ERP. |

## What is where

```
maximo/aceint_1.0.0.dbc               security group ACEINT (MXAPIWODETAIL, MXAPIMETERDATA only), group reassignment,
                                      cron task instance ACEFIELD (MeasurePointWoGenCronTask, every 2 minutes)
maximo/seed_demo.py                   demo data: completed pump work orders with labour and material actuals (REST)

app-connect/MaximoFieldErp/           the App Connect application: three .msgflow files and the ESQL
  Common.esql                         helpers: settings from environment variables, URL encoding, Maximo headers, error text
  WoCostSync.esql                     work order costs -> ERP journal -> write-back
  FieldReadings.esql                  readings: validate, convert, load, reply
  ErpMock.esql                        the ERP stand-in
app-connect/gen_flows.py              writes the .msgflow files (the flows also open in the App Connect Toolkit)
app-connect/build.sh                  builds MaximoFieldErp.bar with ibmint inside the App Connect container image
app-connect/MaximoFieldErp.bar        the built BAR, for a quick start
app-connect/integrationruntime.yaml   the IntegrationRuntime for App Connect on containers

test/readings_batch.json              eight readings, three of them bad on purpose
test/readings_reply_1.json            the answer to the first send
test/readings_reply_2.json            the answer when the same batch is sent again
```

## Quick start

1. Maximo: copy `maximo/aceint_1.0.0.dbc` to `tools/maximo/en/script` and run
   `./runscriptfile.sh -cscript -faceint_1.0.0` from `tools/maximo/internal`. Then in Cron Task Setup,
   `MeasurePointWoGenCronTask` > Reload Request.
2. Create an integration user in group `ACEINT` only, add an API key for it, and store the key in a Secret:
   `kubectl create secret generic maximo-api -n <namespace> --from-literal=MAXIMO_APIKEY="$KEY"`.
3. Import `app-connect/MaximoFieldErp.bar` in the App Connect Dashboard (BAR files > Import BAR file) and copy its
   BAR URL.
4. Fill in the BAR URL and your Manage address in `app-connect/integrationruntime.yaml`, then
   `kubectl apply -f app-connect/integrationruntime.yaml`.
5. Optional demo data: `MAXIMO_API=https://<manage-host>/maximo/api MAXIMO_APIKEY=<admin key> python maximo/seed_demo.py`.
6. Send readings: `curl -X POST -H "Content-Type: application/json" --data @test/readings_batch.json http://<runtime>:7800/field/readings`.

To rebuild the BAR after a change: `bash app-connect/build.sh` (needs podman and access to the App Connect
Enterprise server image; set `ACEBUILD` to a folder podman can mount).

The site (`BEDFORD`), GL pattern (`6000-200-???`) and meter names (`TEMP-F`, `VIBRATIONH`) are those of the Maximo
demo data. Change them in `WoCostSync.esql` and `FieldReadings.esql` for your own data.
