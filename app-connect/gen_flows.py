"""Write the App Connect application MaximoFieldErp (three message flows) in the Toolkit's .msgflow format.
Each flow is declared once below as nodes + connections; ESQL modules live in the .esql files next to them.
    python gen_flows.py   ->   ./MaximoFieldErp/
"""
import pathlib

APP = "MaximoFieldErp"
OUT = pathlib.Path(__file__).parent / APP
NS = {
    "ComIbmWSInput": "ComIbmWSInput.msgnode", "ComIbmWSReply": "ComIbmWSReply.msgnode",
    "ComIbmWSRequest": "ComIbmWSRequest.msgnode", "ComIbmCompute": "ComIbmCompute.msgnode",
    "ComIbmTimeoutNotification": "ComIbmTimeoutNotification.msgnode",
}

# flow name -> (nodes, connections). node: (id, type, label, x, y, attrs). connection: (from, terminal, to)
FLOWS = {
    "erp_mock": (
        [("in", "ComIbmWSInput", "ERP API", 60, 120, {"URLSpecifier": "/erp/*", "messageDomainProperty": "JSON"}),
         ("erp", "ComIbmCompute", "Ledger", 260, 120, {"computeExpression": "esql://routine/#ErpMock.Main", "computeMode": "destinationAndMessage"}),
         ("rep", "ComIbmWSReply", "Reply", 460, 120, {})],
        [("in", "out", "erp"), ("erp", "out", "rep")]),
    "wo_cost_sync": (
        [("tick", "ComIbmTimeoutNotification", "Every minute", 40, 140, {"uniqueIdentifier": "WoCostSync", "operationMode": "automatic", "timeoutInterval": "60"}),
         ("q", "ComIbmCompute", "Build query", 200, 140, {"computeExpression": "esql://routine/#WoCostSync_Query.Main", "computeMode": "destinationAndMessage"}),
         ("get", "ComIbmWSRequest", "Get completed WOs", 370, 140, {"URLSpecifier": "http://localhost:7800/unset", "httpMethod": "GET", "messageDomainProperty": "JSON"}),
         ("map", "ComIbmCompute", "Map to journal", 560, 140, {"computeExpression": "esql://routine/#WoCostSync_Map.Main", "computeMode": "destinationAndMessage"}),
         ("post", "ComIbmWSRequest", "Post journal", 740, 140, {"URLSpecifier": "http://localhost:7800/unset", "httpMethod": "POST", "messageDomainProperty": "JSON"}),
         ("wb", "ComIbmCompute", "Write back", 920, 140, {"computeExpression": "esql://routine/#WoCostSync_WriteBack.Main", "computeMode": "destinationAndMessage"}),
         ("upd", "ComIbmWSRequest", "Update WO", 1100, 140, {"URLSpecifier": "http://localhost:7800/unset", "httpMethod": "POST", "messageDomainProperty": "JSON"}),
         ("err", "ComIbmCompute", "Record failure", 740, 300, {"computeExpression": "esql://routine/#WoCostSync_Failure.Main", "computeMode": "message"})],
        [("tick", "out", "q"), ("q", "out", "get"), ("get", "out", "map"), ("get", "error", "err"), ("get", "failure", "err"),
         ("map", "out", "post"), ("post", "out", "wb"), ("post", "error", "err"), ("post", "failure", "err"),
         ("wb", "out", "upd"), ("upd", "error", "err"), ("upd", "failure", "err")]),
    "field_readings": (
        [("in", "ComIbmWSInput", "Readings API", 40, 140, {"URLSpecifier": "/field/readings", "messageDomainProperty": "JSON"}),
         ("val", "ComIbmCompute", "Validate and map", 230, 140, {"computeExpression": "esql://routine/#FieldReadings_Validate.Main", "computeMode": "destinationAndMessage"}),
         ("load", "ComIbmWSRequest", "Load reading", 430, 80, {"URLSpecifier": "http://localhost:7800/unset", "httpMethod": "POST", "messageDomainProperty": "JSON"}),
         ("ok", "ComIbmCompute", "Record loaded", 630, 40, {"computeExpression": "esql://routine/#FieldReadings_Loaded.Main", "computeMode": "message"}),
         ("bad", "ComIbmCompute", "Record refused", 630, 140, {"computeExpression": "esql://routine/#FieldReadings_Refused.Main", "computeMode": "message"}),
         ("rep", "ComIbmWSReply", "Reply", 430, 240, {})],
        [("in", "out", "val"), ("val", "out", "load"), ("val", "out1", "rep"), ("load", "out", "ok"),
         ("load", "error", "bad"), ("load", "failure", "bad")]),
}


def esc(v):
    return str(v).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def msgflow(name, nodes, conns):
    ids = {n[0]: f"FCMComposite_1_{i + 1}" for i, n in enumerate(nodes)}
    used = sorted({n[1] for n in nodes})
    xmlns = " ".join(f'xmlns:{NS[t]}="{NS[t]}"' for t in used)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<ecore:EPackage xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" {xmlns} '
           'xmlns:ecore="http://www.eclipse.org/emf/2002/Ecore" xmlns:eflow="http://www.ibm.com/wbi/2005/eflow" '
           f'xmlns:utility="http://www.ibm.com/wbi/2005/eflow_utility" nsURI="{name}.msgflow" nsPrefix="{name}.msgflow">',
           '  <eClassifiers xmi:type="eflow:FCMComposite" name="FCMComposite_1">',
           '    <eSuperTypes href="http://www.ibm.com/wbi/2005/eflow#//FCMBlock"/>',
           f'    <translation xmi:type="utility:TranslatableString" key="{name}" bundleName="{name}" pluginId="{APP}"/>',
           '    <composition>']
    for nid, typ, label, x, y, attrs in nodes:
        a = " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items())
        out.append(f'      <nodes xmi:type="{NS[typ]}:FCMComposite_1" xmi:id="{ids[nid]}" location="{x},{y}" {a}>')
        out.append(f'        <translation xmi:type="utility:ConstantString" string="{esc(label)}"/>')
        out.append('      </nodes>')
    for i, (src, term, dst) in enumerate(conns):
        out.append(f'      <connections xmi:type="eflow:FCMConnection" xmi:id="FCMConnection_{i + 1}" targetNode="{ids[dst]}" '
                   f'sourceNode="{ids[src]}" sourceTerminalName="OutTerminal.{term}" targetTerminalName="InTerminal.in"/>')
    out += ['    </composition>', '    <propertyOrganizer/>', '    <stickyBoard/>', '  </eClassifiers>', '</ecore:EPackage>', '']
    return "\n".join(out)


OUT.mkdir(parents=True, exist_ok=True)
for name, (nodes, conns) in FLOWS.items():
    (OUT / f"{name}.msgflow").write_text(msgflow(name, nodes, conns), encoding="utf-8")
(OUT / "application.descriptor").write_text(
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<ns2:appDescriptor xmlns="http://com.ibm.etools.mft.descriptor.base" xmlns:ns2="http://com.ibm.etools.mft.descriptor.app">\n'
    '  <references/>\n</ns2:appDescriptor>\n', encoding="utf-8")
(OUT / ".project").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
  <name>{APP}</name>
  <comment></comment>
  <projects></projects>
  <buildSpec>
    <buildCommand><name>com.ibm.etools.mft.applib.applibbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.applib.applibresourcevalidator</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.connector.policy.ui.PolicyBuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.applib.mbprojectbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.msg.validation.dfdl.mlibdfdlbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.flow.adapters.adapterbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.flow.sca.scabuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.msg.validation.dfdl.mbprojectresourcesbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.esql.lang.esqllangbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.map.builder.mslmappingbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.flow.msgflowxsltbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.flow.msgflowbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.decision.service.ui.decisionservicerulebuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.pattern.capture.PatternBuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.json.builder.JSONBuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.restapi.ui.restApiDefinitionsBuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.policy.ui.policybuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.msg.assembly.messageAssemblyBuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.esql.lang.esqllangbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.bar.ext.barbuilder</name><arguments></arguments></buildCommand>
    <buildCommand><name>com.ibm.etools.mft.unittest.ui.TestCaseBuilder</name><arguments></arguments></buildCommand>
  </buildSpec>
  <natures>
    <nature>com.ibm.etools.msgbroker.tooling.applicationNature</nature>
    <nature>com.ibm.etools.msgbroker.tooling.messageBrokerProjectNature</nature>
  </natures>
</projectDescription>
""", encoding="utf-8")
print("wrote", sorted(p.name for p in OUT.iterdir()))
